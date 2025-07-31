function setupCategoryValidation() {
  document.querySelectorAll('.file-upload-form').forEach(form => {
    const select = form.querySelector('select[name="category"]');
    const button = form.querySelector('.upload-btn');
    const warning = form.querySelector('.category-warning');
    if (!select || !button) return;
    function update() {
      const valid = select.value !== '' && select.value !== null;
      button.disabled = !valid;
      if (valid) {
        button.style.opacity = '';
        button.style.cursor = '';
        warning && warning.classList.add('d-none');
      } else {
        button.style.opacity = '0.6';
        button.style.cursor = 'not-allowed';
        warning && warning.classList.remove('d-none');
      }
    }
    select.addEventListener('change', update);
    update();
  });
}

document.addEventListener('DOMContentLoaded', setupCategoryValidation);