(function(){
  if(window.__notesAssignInit__) return; window.__notesAssignInit__=true;
  function metaCsrf(){
    const m=document.querySelector('meta[name="csrf-token"]');
    return m&&m.content?m.content:null;
  }
  document.addEventListener('DOMContentLoaded',function(){
    const wrap=document.querySelector('#notes-form');
    if(!wrap){console.warn('notes: wrapper not found'); return;}
    const btn=wrap.querySelector('#add_note_btn');
    const txt=wrap.querySelector('#new_note');
    const container=wrap.querySelector('.card-body');
    const cid=wrap.getAttribute('data-case-id');
    if(!btn||!txt||!container){console.warn('notes: missing input or container'); return;}
    btn.addEventListener('click',function(ev){
      ev.preventDefault();
      const note=(txt.value||'').trim();
      if(!note){txt.classList.add('is-invalid');return;}
      txt.classList.remove('is-invalid');
      const headers={'Content-Type':'application/json'};
      const tokenInput=wrap.querySelector('input[name="csrf_token"]');
      const token=tokenInput&&tokenInput.value?tokenInput.value:metaCsrf();
      if(token) headers['X-CSRFToken']=token;
      const url=cid?`/cases/${cid}/add_note`:(btn.dataset.postUrl||btn.getAttribute('data-post-url'));
      if(!url){console.error('notes: no target URL'); return;}
      fetch(url,{method:'POST',headers,body:JSON.stringify({new_note:note})})
        .then(r=>{if(!r.ok) throw r; return r.json();})
        .then(data=>{
          if(data&&data.html){
            container.insertAdjacentHTML('afterbegin',data.html);
            txt.value='';
          }
        })
        .catch(err=>console.error('notes: submit failed',err));
    });
  });
})();