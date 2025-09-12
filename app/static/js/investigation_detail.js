(function() {
  const btn = document.getElementById('add-note-btn');
  if (!btn || btn.dataset.bound) return;
  btn.dataset.bound = 'true';
  btn.addEventListener('click', function() {
    const textarea = document.querySelector('textarea[name="text"]');
    if (!textarea || !textarea.value.trim()) {
      textarea.classList.add('is-invalid');
      return;
    }
    fetch(window.location.pathname + '/notes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
      },
      body: JSON.stringify({ text: textarea.value.trim() })
    })
      .then(r => {
        if (!r.ok) throw new Error();
        return r.text();
      })
      .then(html => {
        const list = document.getElementById('notes-list');
        const empty = list.querySelector('.empty-state');
        if (empty) empty.remove();
        list.insertAdjacentHTML('afterbegin', html);
        textarea.value = '';
      })
      .catch(() => alert('Hiba a megjegyzés mentésekor'));
  });
})();
