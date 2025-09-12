(function() {
  const form = document.getElementById('upload-form');
  if (!form) return;

  const handler = function(e) {
    e.preventDefault();
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
        const container = document.getElementById('attachments');
        const empty = container.querySelector('.empty-state');
        if (empty) empty.remove();
        let list = container.querySelector('ul');
        if (!list) {
          list = document.createElement('ul');
          list.className = 'list-group list-group-flush mb-0';
          container.appendChild(list);
        }
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
          <div>${data.filename} <span class="badge bg-secondary ms-2">${data.category}</span></div>
          <div class="text-nowrap"><small class="text-muted">${data.uploaded_at}</small>
            <a href="${window.location.pathname}/download/${data.id}" class="btn btn-sm btn-outline-primary ms-2">Letöltés</a>
          </div>`;
        list.prepend(li);
        fileInput.value = '';
      })
      .catch(() => alert('Hiba a fájl feltöltésekor'));
  };

  const btn = document.getElementById('upload-btn');
  if (btn) {
    btn.addEventListener('click', handler);
  } else {
    form.addEventListener('submit', handler);
  }
})();