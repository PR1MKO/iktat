(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  ready(function () {
    var btn = document.getElementById('ack-cookie');
    if (!btn) return;
    var meta = document.querySelector('meta[name="csrf-token"]');
    var token = meta ? meta.content : '';
    btn.addEventListener('click', function () {
      fetch('/ack_cookie_notice', {
        method: 'POST',
        headers: { 'X-CSRFToken': token }
      }).then(function (resp) {
        if (resp.status === 204) {
          var banner = document.getElementById('cookie-banner');
          if (banner) banner.style.display = 'none';
        }
      }).catch(function () {
        /* no-op; keep UI unchanged on error */
      });
    });
  });
})();
