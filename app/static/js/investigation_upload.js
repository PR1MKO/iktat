(function() {
  const btn = document.getElementById('upload-btn');
  if (!btn) return;
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    const form = document.getElementById('upload-form');
    const fileInput = form.querySelector('input[type="file"]');
    const category = form.querySelector('select[name="category"]').value;
    if (!fileInput.files.length || !category) {
      return;
    }
    const fd = new FormData();
    fd.append('csrf_token', form.querySelector('input[name="csrf_token"]').value);
    fd.append('category', category);
    fd.append('file', fileInput.files[0]);
    fetch(form.getAttribute('action') || window.location.pathname + '/upload', {
      method: 'POST',
      body: fd
    })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error();
      const list = document.getElementById('attachments-list');
      const li = document.createElement('li');
      li.dataset.id = data.id;
      li.textContent = `${data.filename} – ${data.category} – ${data.uploaded_at}`;
      list.prepend(li);
      fileInput.value = '';
    })
    .catch(() => alert('Hiba a fájl feltöltésekor'));
  });
})();