// Auto-dismiss Bootstrap alerts without inline JS (CSP-safe)
(function () {
  function closeAlerts() {
    var nodes = document.querySelectorAll('.alert');
    nodes.forEach(function (el) {
      if (el.dataset.autoDismiss === 'false') return;
      var ms = parseInt(el.dataset.autoDismissMs || '5000', 10);
      setTimeout(function () {
        try {
          if (window.bootstrap && window.bootstrap.Alert) {
            var inst = window.bootstrap.Alert.getOrCreateInstance(el);
            inst.close();
          } else {
            el.classList.remove('show');
            if (el.parentNode) el.parentNode.removeChild(el);
          }
        } catch (e) {
          /* noop */
        }
      }, ms);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', closeAlerts);
  } else {
    closeAlerts();
  }
})();