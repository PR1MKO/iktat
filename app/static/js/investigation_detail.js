(function() {
  const btn = document.getElementById('add-note-btn');
  if (!btn || btn.dataset.bound) return;
  btn.dataset.bound = 'true';
  
  function showInlineWarning(message) {
    const container = btn.parentElement || btn.closest('.card-body') || document.body;
    let warn = container.querySelector('.alert[data-note-error]');
    if (!warn) {
      warn = document.createElement('div');
      warn.className = 'alert alert-warning';
      warn.setAttribute('role', 'alert');
      warn.setAttribute('data-auto-dismiss', 'false');
      warn.setAttribute('data-note-error', 'true');
      const reference =
        container.querySelector('form') ||
        container.querySelector('textarea[name="text"]') ||
        container.querySelector('#add-note-btn') ||
        container.firstChild;
      if (reference && reference.parentNode === container) {
        container.insertBefore(warn, reference);
      } else {
        container.insertBefore(warn, container.firstChild);
      }
    }
    warn.textContent = message;
  }

  function clearInlineWarning() {
    const container = btn.parentElement || btn.closest('.card-body') || document.body;
    const warn = container.querySelector('.alert[data-note-error]');
    if (warn) {
      warn.remove();
    }
  }
  
  btn.addEventListener('click', function() {
    const textarea = document.querySelector('textarea[name="text"]');
    if (!textarea || !textarea.value.trim()) {
      if (textarea) {
        textarea.classList.add('is-invalid');
      }
      return;
    }
	
    const basePath = window.location.pathname.replace(/\/$/, '');
    const targetUrl = btn.dataset.notesUrl || basePath + '/notes';
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    const payload = { text: textarea.value.trim() };
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfInput ? csrfInput.value : ''
    };
	
    fetch(targetUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    })
      .then(async (res) => {
        if (!res.ok) {
          const message = res.status === 403
            ? 'Nincs jogosultság megjegyzést hozzáadni ehhez a vizsgálathoz.'
            : 'Hiba történt a megjegyzés mentése közben.';
          showInlineWarning(message);
          return null;
        }

        const contentType = res.headers ? res.headers.get('Content-Type') || '' : '';
        if (contentType.includes('application/json')) {
          return res.json();
        }
        return res.text();
      })
      .then((data) => {
        if (!data) {
          return;
        }

        const html = typeof data === 'string' ? data : data && data.html;
        const list =
          document.getElementById('notes-list') ||
          document.querySelector('#notes') ||
          document.querySelector('.notes-list');

        if (!list || !html) {
          window.location.reload();
          return;
        }
		
        const empty = list.querySelector('.empty-state');
        if (empty) empty.remove();
        list.insertAdjacentHTML('afterbegin', html);
        textarea.value = '';
        textarea.classList.remove('is-invalid');
        clearInlineWarning();
      })
      .catch(() => {
        showInlineWarning('Hiba történt a megjegyzés mentése közben.');
      });
  });
})();
