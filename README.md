# Stato dei passi per la webapp di Poschiavo

Questa integrazione aggiunge quattro indicatori nella fascia del meteo e aggiorna `data/passi.json` ogni ora con gli avvisi pubblicati dal portale stradale ufficiale dei Grigioni.

## File da copiare nel repository

- Sostituisci `index.html` con il file incluso.
- Copia `pass-status.js` nella stessa cartella di `index.html`.
- Copia `data/passi.json` nella cartella `data/`.
- Copia `scripts/update_pass_status.py` nella cartella `scripts/`.
- Copia `.github/workflows/aggiorna-passi.yml` mantenendo la stessa struttura di cartelle.

Conserva gli altri file già usati dalla pagina, come `manifest.webmanifest`, `sw.js` e le icone.

## Attivazione su GitHub

1. Nel repository apri **Settings → Actions → General** e consenti al token dei workflow di scrivere nel repository, se l'organizzazione non lo consente già.
2. Salva i file sul branch predefinito. Il workflow si avvia ogni ora al minuto 17 UTC; puoi anche lanciarlo manualmente da **Actions → Aggiorna stato passi → Run workflow**.
3. Se GitHub Pages pubblica direttamente dal branch, il commit di `data/passi.json` aggiorna il file pubblicato. Se il sito viene pubblicato da un workflow di deploy separato, integra il passaggio di deploy dopo la generazione dei dati: i commit fatti con il token del workflow non avviano automaticamente altri workflow `on: push`.

## Stati mostrati

- **Aperto / Chiuso / Limitazioni / Avviso** quando il portale riporta una segnalazione riconoscibile.
- **Nessun avviso** quando il portale non restituisce una segnalazione attiva per quel passo. Non viene presentato come apertura certa.
- **Non disponibile** se il file manca, l'aggiornamento supera tre ore o la richiesta fallisce.

L'aggiornamento dipende dalla pubblicazione delle segnalazioni da parte del Cantone. Il collector usa l'endpoint JSON attualmente caricato dalla mappa (`/Map/GetRoadStatus`); il portale non lo documenta come API pubblica, quindi il formato potrebbe cambiare. Se la risposta cambia, il workflow fallisce senza sostituire i dati precedenti e il riquadro segnala il dato come non aggiornato.
