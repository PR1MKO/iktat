(function () {
  function getCaseId(node) {
    if (!node) return null;
    var wrap = node.closest && node.closest('#notes-form, [data-case-id]');
    if (wrap && wrap.dataset && wrap.dataset.caseId) {
      return wrap.dataset.caseId;
    }
    var ancestor = node.closest && node.closest('[data-case-id]');
    if (ancestor && ancestor.dataset && ancestor.dataset.caseId) {
      return ancestor.dataset.caseId;
    }
    var match = (window.location.pathname || '').match(/\/cases\/(\d+)/);
    return match ? match[1] : null;
  }

  function getCsrf(node) {
    var root = (node && node.closest && node.closest('#notes-form')) || document;
    var hidden = root.querySelector('input[name="csrf_token"]') || document.querySelector('input[name="csrf_token"]');
    if (hidden && hidden.value) {
      return hidden.value;
    }
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : null;
  }

  function findNotesInput(start) {
    if (!start) return null;
    var wrap = start.closest && start.closest('#notes-form');
    if (wrap) {
      return wrap.querySelector('#new_note');
    }
    return document.querySelector('#new_note');
  }

  function findNotesList(start) {
    if (!start) return null;
    var wrap = start.closest && start.closest('#notes-form');
    if (wrap) {
      return wrap.querySelector('#notes-list') || wrap.querySelector('.card-body') || wrap;
    }
    return document.querySelector('#notes-list');
  }

  function postNote(btn) {
    var input = findNotesInput(btn);
    if (!input) return;
    var note = (input.value || '').trim();
    if (!note) return;
    var caseId = getCaseId(btn);
    if (!caseId) {
      console.warn('notes: case id not resolved');
      return;
    }
    var headers = { 'Content-Type': 'application/json' };
    var csrf = getCsrf(btn);
    if (csrf) {
      headers['X-CSRFToken'] = csrf;
    }
    fetch('/cases/' + caseId + '/add_note', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ new_note: note })
    })
      .then(function (resp) {
        if (!resp.ok) {
          throw resp;
        }
        return resp.json();
      })
      .then(function (data) {
        if (!data || !data.html) {
          return;
        }
        var list = findNotesList(btn) || input.closest('#notes-form') || document;
        list.innerHTML = data.html;
        input.value = '';
      })
      .catch(function (err) {
        console.error('notes: submit failed', err);
      });
  }

  function bindButton(btn) {
    if (!btn || btn.dataset.notesBound === '1') {
      return;
    }
    var input = findNotesInput(btn);
    if (!input) {
      return;
    }
    btn.addEventListener('click', function (ev) {
      ev.preventDefault();
      postNote(btn);
    });
    btn.dataset.notesBound = '1';
  }

  function initNotes() {
    var buttons = document.querySelectorAll('#add_note_btn');
    if (!buttons.length) {
      return;
    }
    buttons.forEach(bindButton);
  }

  window.attachCaseNotesHandlers = function () {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initNotes, { once: true });
    } else {
      initNotes();
    }
  };

  window.attachCaseNotesHandlers();
})();