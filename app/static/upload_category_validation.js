(() => {
  const form = document.querySelector('form.file-upload-form');
  if (!form || form.dataset.catValidationAttached) return;
  form.dataset.catValidationAttached = '1';

  const select  = form.querySelector('select[name="category"]');
  const button  = form.querySelector('.upload-btn');
  const warning = form.querySelector('.category-warning');

  function update() {
    const isValid = !!(select && select.value);
    if (button) button.disabled = !isValid;
    if (warning) warning.classList.toggle('d-none', isValid);
    if (select) {
      select.setAttribute('aria-invalid', isValid ? 'false' : 'true');
      select.classList.toggle('is-invalid', !isValid);
    }
  }

  // Enable/disable on category change
  form.addEventListener('change', (e) => {
    if (e.target === select) update();
  });

  // Guard submit: only allow when category chosen; otherwise prevent + show warning
  form.addEventListener('submit', (e) => {
    const isValid = !!(select && select.value);
    if (!isValid) {
      e.preventDefault();
      update
      // move focus to the field and ensure it is visible
      try { select.focus({ preventScroll: false }); } catch (_) { select.focus(); }
      try { select.scrollIntoView({ block: 'center' }); } catch (_) {}
    }
  });

  // Initial state on load
  update();
})();
