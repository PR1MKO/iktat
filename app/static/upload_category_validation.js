function setupCategoryValidation() {
  document.querySelectorAll('.file-upload-form').forEach(form => {
    if (form.dataset.catValidationAttached === '1') return;
    const select = form.querySelector('select[name="category"]');
    const button = form.querySelector('.upload-btn');
    const warning = form.querySelector('.category-warning');
    if (!select || !button) return;

    function update() {
      const isValid = select.selectedIndex > 0;
      button.disabled = !isValid;
      if (warning) {
        warning.classList.toggle('d-none', isValid);
      }
      select.setAttribute('aria-invalid', isValid ? 'false' : 'true');
    }

    select.addEventListener('change', update);
    update();

    // Block submission when no category is selected
    form.addEventListener('submit', event => {
      if (!form.checkValidity() || !select.value) {
        event.preventDefault();
        try { form.reportValidity(); } catch (_) {}
        update();
      }
    });
    form.dataset.catValidationAttached = '1';
  });
}

function initUploadCategoryValidation() {
  try {
    setupCategoryValidation();
  } catch (e) {
    console.warn(e);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initUploadCategoryValidation, { once: true });
} else {
  initUploadCategoryValidation();
}
window.addEventListener('htmx:load', initUploadCategoryValidation);
window.addEventListener('htmx:afterSwap', initUploadCategoryValidation);
