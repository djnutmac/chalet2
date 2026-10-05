#!/usr/bin/env python3
"""Scarica gli avvisi stradali pubblici del Canton Grigioni e crea data/passi.json."""
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ENDPOINT = "https://www.strassen.gr.ch/Map/GetRoadStatus"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "passi.json"
PASSES = [
    {"id": "bernina", "name": "Bernina", "aliases": ["berninastrasse", "strada del bernina", "bernina pass"]},
    {"id": "forcola", "name": "Forcola", "aliases": ["forcola di livigno strasse", "forcola di livigno", "strada della forcola", "forcola strasse"]},
    {"id": "maloja", "name": "Maloja", "aliases": ["malojastrasse", "strada del maloja", "maloja pass"]},
    {"id": "julier", "name": "Julier", "aliases": ["julierstrasse", "strada dello julier", "strada del julier", "julier pass"]},
]

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

class BlockParser(HTMLParser):
    """Estrae il nome della strada e il testo breve dello stato."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.road, self.state = [], []
        self.current = None
        self.depth = 0
        self.target_depth = None
    def handle_starttag(self, tag, attrs):
        if tag != "div":
            return
        self.depth += 1
        classes = dict(attrs).get("class", "").split()
        if "road" in classes or "state" in classes:
            self.current = "road" if "road" in classes else "state"
            self.target_depth = self.depth
    def handle_endtag(self, tag):
        if tag != "div":
            return
        if self.target_depth == self.depth:
            self.current = None
            self.target_depth = None
        self.depth = max(0, self.depth - 1)
    def handle_data(self, data):
        if self.current == "road":
            self.road.append(data)
        elif self.current == "state":
            self.state.append(data)

def normalize(value):
    value = html.unescape(str(value or "")).replace("ß", "ss")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def visible_text(fragment):
    parser = TextParser()
    parser.feed(str(fragment or ""))
    return " ".join(" ".join(parser.parts).split())

def details(record):
    raw = str(record.get("MessageHtml") or record.get("messageHtml") or "")
    parser = BlockParser()
    parser.feed(raw)
    all_text = visible_text(raw)
    road = " ".join(" ".join(parser.road).split())
    state = " ".join(" ".join(parser.state).split())
    icon = record.get("IconFile") or record.get("conditionIconUrl") or record.get("eventIconUrl") or ""
    return road, state, all_text, normalize(icon)

def matches(pass_info, road, all_text):
    road_n, text_n = normalize(road), normalize(all_text)
    for alias in pass_info["aliases"]:
        alias_n = normalize(alias)
        if alias_n and (alias_n in road_n or alias_n in text_n):
            return True
    return False

def classify(state, icon):
    state_n = normalize(state)
    if any(mark in icon for mark in ("wintersperre", "gesperrt", "closed")):
        return "closed"
    if any(mark in state_n for mark in ("wintersperre", "gesperrt", "chiuso tra", "strada chiusa", "passo chiuso", "geschlossen zwischen", "pass geschlossen")):
        return "closed"
    if any(mark in icon for mark in ("schneebedeckt", "ketten", "chains", "limited")):
        return "limited"
    if any(mark in state_n for mark in ("kettenpflicht", "kettenobligatorium", "obbligo catene", "catene obbligatorie", "schneebedeckt", "neve sulla strada", "snow covered")):
        return "limited"
    if any(mark in state_n for mark in ("offen", "aperto", "open")):
        return "open"
    return "notice"

def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OSError):
        return 0

def main():
    request = Request(ENDPOINT, headers={
        # Il portale serve i dati della mappa con una richiesta simile a quella del browser.
        # L'identificativo personalizzato usato inizialmente riceveva una risposta HTTP vuota
        # da GitHub Actions, che causava JSONDecodeError.
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-CH,it;q=0.9,de-CH;q=0.8,de;q=0.7,en;q=0.6",
        "Cache-Control": "no-cache",
        "Referer": "https://www.strassen.gr.ch/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    })
    with urlopen(request, timeout=40) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "non specificato")
        status_code = response.status
    if not raw.strip():
        raise RuntimeError(
            f"strassen.gr.ch ha restituito una risposta vuota (HTTP {status_code}, "
            f"Content-Type: {content_type}). Il server potrebbe rifiutare la richiesta "
            "da GitHub Actions; il file data/passi.json non è stato modificato."
        )
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = raw[:240].decode("utf-8", errors="replace").replace("\n", " ").strip()
        raise RuntimeError(
            f"strassen.gr.ch non ha restituito JSON valido (HTTP {status_code}, "
            f"Content-Type: {content_type}). Inizio risposta: {preview!r}"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
        raise RuntimeError("La risposta di strassen.gr.ch non contiene la lista 'messages'; non aggiorno il file.")
    passes = []
    for pass_info in PASSES:
        candidates = []
        for record in payload["messages"]:
            if not isinstance(record, dict):
                continue
            road, state, all_text, icon = details(record)
            if matches(pass_info, road, all_text):
                status = classify(state, icon)
                candidates.append({
                    "id": pass_info["id"], "name": pass_info["name"], "status": status,
                    "detail": (all_text or state or road or "Avviso stradale")[:500],
                    "reportedAt": record.get("MessageTime") or None, "road": road or None,
                    "icon": icon or None,
                    "_priority": {"closed": 5, "limited": 4, "open": 3, "notice": 2}.get(status, 1),
                    "_time": parse_time(record.get("MessageTime")),
                })
        if candidates:
            chosen = max(candidates, key=lambda x: (x["_priority"], x["_time"]))
            chosen.pop("_priority", None)
            chosen.pop("_time", None)
            passes.append(chosen)
        else:
            passes.append({
                "id": pass_info["id"], "name": pass_info["name"], "status": "no_report",
                "detail": "Nessun avviso attivo trovato per questa strada nel portale cantonale.",
                "reportedAt": None, "road": None, "icon": None,
            })
    result = {
        "source": "https://www.strassen.gr.ch/", "endpoint": ENDPOINT,
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "passes": passes,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Aggiornato {OUTPUT.relative_to(Path(__file__).resolve().parents[1])}")

if __name__ == "__main__":
    main()
