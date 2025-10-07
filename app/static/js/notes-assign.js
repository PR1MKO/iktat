(function () {
  function trigger() {
    if (typeof window.attachCaseNotesHandlers === 'function') {
      window.attachCaseNotesHandlers();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', trigger, { once: true });
  } else {
    trigger();
  }
})();