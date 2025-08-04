(function() {
  try {
    function send(eventType, element, value, extra) {
      try {
        fetch('/track', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            event_type: eventType,
            element: element,
            value: value,
            extra: extra
          })
        });
      } catch (err) {}
    }

    window.addEventListener('load', function() {
      send('load', 'window', window.location.pathname, { page: window.location.pathname });
    }, { passive: true });

    window.addEventListener('click', function(e) {
      try {
        var target = e.target.closest('button, a, input[type="button"], input[type="submit"]');
        if (!target) return;
        var el = target.tagName.toLowerCase();
        if (target.id) el += '#' + target.id;
        var val = target.value || target.textContent || '';
        send('click', el, val, { page: window.location.pathname });
      } catch (err) {}
    }, { passive: true });

    window.addEventListener('change', function(e) {
      try {
        var t = e.target;
        if (!t) return;
        var el = t.tagName.toLowerCase();
        if (t.id) el += '#' + t.id;
        var val = '';
        if ('value' in t && t.type !== 'password') {
          val = t.value;
        }
        send('change', el, val, { page: window.location.pathname });
      } catch (err) {}
    }, { passive: true });

    window.addEventListener('submit', function(e) {
      try {
        var form = e.target;
        var el = form.tagName.toLowerCase();
        if (form.id) el += '#' + form.id;
        send('submit', el, form.action || '', { page: window.location.pathname });
      } catch (err) {}
    }, { passive: true });
  } catch (err) {}
})();