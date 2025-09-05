// upload_helpers.js
(function () {
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!form.classList || !form.classList.contains('file-upload-form')) return;

    const cat = form.querySelector('select[name="category"]');
    if (!form.checkValidity() || !cat || !cat.value) {
      e.preventDefault();
      try { form.reportValidity(); } catch (_) {}
      return;
    }
    // Native submit proceeds when valid.
  }, { capture: true });
})();