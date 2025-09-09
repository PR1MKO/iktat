import { $ } from '../lib/dom.js';

(function init() {
  const form = $('.needs-validation');
  if (form) {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    }, false);
  }

  const role = $('#role');
  const leiro = $('#default_leiro_id');

  function toggle() {
    const isExpert = role && role.value === 'szakértő';
    if (!leiro) return;
    leiro.disabled = !isExpert;
    if (isExpert) {
      leiro.setAttribute('required', 'required');
    } else {
      leiro.removeAttribute('required');
      leiro.value = '0';
    }
  }

  if (role) role.addEventListener('change', toggle);
  toggle();
})();