import { $ } from '../lib/dom.js';

(function init() {
  const form = $('.needs-validation');
  if (!form) return;
  form.addEventListener('submit', event => {
    if (!form.checkValidity()) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.classList.add('was-validated');
  }, false);
})();