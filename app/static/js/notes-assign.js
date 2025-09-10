(function(){
  if(window.__notesAssignInit__) return; window.__notesAssignInit__=true;
  function csrf(){const m=document.querySelector('meta[name="csrf-token"]');return m&&m.content?m.content:null}
  function q(sel,root){return (root||document).querySelector(sel)}
  document.addEventListener('DOMContentLoaded',function(){
    const wrap=q('#notes-form'); if(!wrap) return;
    const btn=q('#add_note_btn'); const txt=q('#new_note');
    const container=q('#notes-form .card-body');
    const cid=wrap.getAttribute('data-case-id');
    if(!btn||!txt||!container||!cid) return;
    btn.addEventListener('click',function(ev){
      ev.preventDefault(); const val=(txt.value||'').trim();
      if(!val){txt.classList.add('is-invalid');return}
      const headers={'Content-Type':'application/json'}; const token=csrf(); if(token) headers['X-CSRFToken']=token;
      fetch(`/cases/${cid}/add_note`,{method:'POST',headers,body:JSON.stringify({new_note:val})})
        .then(r=>{if(!r.ok) throw new Error('request_failed'); return r.json()})
        .then(data=>{ if(data&&data.html){container.insertAdjacentHTML('afterbegin',data.html); txt.value=''; txt.classList.remove('is-invalid')} else {alert('Nem található notes container vagy üres válasz.')} })
        .catch(()=>alert('Hiba a megjegyzés mentésekor'));
    });
  });
})();