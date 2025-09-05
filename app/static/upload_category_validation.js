function setupCategoryValidation() {
  document.querySelectorAll('.file-upload-form').forEach(form => {
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
  });
}

document.addEventListener('DOMContentLoaded', setupCategoryValidation);
