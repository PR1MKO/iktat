// Ensure notes lists stay scrolled to the latest entries.
(function () {
  function scrollToBottom(el) {
    try {
      el.scrollTop = el.scrollHeight;
    } catch (_) {
      /* noop */
    }
  }

  var raf = typeof window !== 'undefined' && window.requestAnimationFrame
    ? window.requestAnimationFrame.bind(window)
    : function (cb) { return setTimeout(cb, 0); };

  function initNode(el) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function handleLoad() {
        scrollToBottom(el);
      }, { once: true });
    } else {
      raf(function () {
        scrollToBottom(el);
      });
    }

    var observer = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i += 1) {
        var mutation = mutations[i];
        if (mutation.type === 'childList' && mutation.addedNodes && mutation.addedNodes.length) {
          scrollToBottom(el);
          break;
        }
      }
    });

    observer.observe(el, { childList: true });
  }

  function initAll() {
    var targets = document.querySelectorAll('[data-scroll-bottom="true"]');
    Array.prototype.forEach.call(targets, function (el) {
      initNode(el);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll, { once: true });
  } else {
    initAll();
  }
})();