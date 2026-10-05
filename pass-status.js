/* Stato passi da data/passi.json, generato ogni ora dal workflow GitHub. */
(function(){
  var grid=document.getElementById('passi-grid');
  var title=document.getElementById('passi-title');
  var updated=document.getElementById('passi-updated');
  if(!grid||!title||!updated)return;
  var language=0,data=null;
  var ids=['bernina','forcola','maloja','julier'];
  var words=[
    {title:'Stato passi',updated:'Aggiornato',open:'Aperto',closed:'Chiuso',limited:'Limitazioni',notice:'Avviso',no_report:'Nessun avviso',unknown:'Non disponibile',names:['Bernina','Forcola','Maloja','Julier']},
    {title:'Pass status',updated:'Updated',open:'Open',closed:'Closed',limited:'Restrictions',notice:'Notice',no_report:'No alert',unknown:'Unavailable',names:['Bernina','Forcola','Maloja','Julier']},
    {title:'Passstatus',updated:'Aktualisiert',open:'Offen',closed:'Geschlossen',limited:'Einschränkungen',notice:'Hinweis',no_report:'Keine Meldung',unknown:'Nicht verfügbar',names:['Bernina','Forcola','Maloja','Julier']}
  ];
  function timeText(value){
    if(!value)return '';
    var d=new Date(value);
    if(isNaN(d.getTime()))return '';
    var locale=['it-IT','en-GB','de-CH'][language]||'it-IT';
    return new Intl.DateTimeFormat(locale,{hour:'2-digit',minute:'2-digit',timeZone:'Europe/Zurich'}).format(d);
  }
  function render(){
    var w=words[language]||words[0],stale=false;
    title.textContent=w.title;
    if(data&&data.updatedAt){
      var age=Date.now()-new Date(data.updatedAt).getTime();
      stale=!isFinite(age)||age>3*60*60*1000;
    }else stale=true;
    grid.textContent='';
    ids.forEach(function(id,i){
      var item=data&&Array.isArray(data.passes)?data.passes.find(function(x){return x.id===id}):null;
      var status=item&&item.status||'unknown';
      if(['open','closed','limited','notice','no_report'].indexOf(status)<0)status='unknown';
      if(stale)status='unknown';
      var card=document.createElement('div');card.className='pass-card';
      card.title=item&&item.detail?item.detail:(stale?'Ultimo aggiornamento non recente.':'');
      var name=document.createElement('span');name.className='pass-name';name.textContent=w.names[i];
      var value=document.createElement('span');value.className='pass-value '+status;value.textContent=w[status];
      card.appendChild(name);card.appendChild(value);grid.appendChild(card);
    });
    var stamp=data&&data.updatedAt?timeText(data.updatedAt):'';
    updated.textContent=stamp&&!stale?(w.updated+' '+stamp):w.unknown;
  }
  function load(){
    fetch('data/passi.json?ts='+Date.now(),{cache:'no-store'})
      .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
      .then(function(j){if(!j||!Array.isArray(j.passes))throw new Error('Formato dati non valido');data=j;render()})
      .catch(function(){data=null;render()});
  }
  document.addEventListener('mlin',function(e){if(e&&typeof e.detail==='number'&&e.detail>=0&&e.detail<words.length){language=e.detail;render()}});
  document.addEventListener('visibilitychange',function(){if(!document.hidden)load()});
  load();
  setInterval(load,15*60*1000);
})();
