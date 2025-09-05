// case_upload_block.js — extracted from includes/case_macros.html (CSP-safe)
(function () {
  function attachOnce() {
    document.querySelectorAll('.file-upload-form').forEach(function (form) {
      if (form.dataset.catValidationAttached === '1') return;

      var select = form.querySelector('select[name="category"]');
      var button = form.querySelector('.upload-btn');
      if (!select || !button) { form.dataset.catValidationAttached = '1'; return; }

      function update() {
        var ok = !!select.value;
        button.disabled = !ok;
        select.setAttribute('aria-invalid', ok ? 'false' : 'true');
      }

      select.addEventListener('change', update);
      update();

      form.addEventListener('submit', function (ev) {
        if (!form.checkValidity() || !select.value) {
          ev.preventDefault();
          try { form.reportValidity(); } catch (e) {}
          update();
          return;
        }
      });

      form.dataset.catValidationAttached = '1';
    });
  }

  function init() {
    try { attachOnce(); } catch (e) { console.warn(e); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
  if (window.addEventListener) {
    window.addEventListener('htmx:load', init);
    window.addEventListener('htmx:afterSwap', init);
  }
})();