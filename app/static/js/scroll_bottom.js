(function () {
  "use strict";

  // How close to the bottom we consider "stuck" (px)
  var STICKY_THRESHOLD = 120;

  function isNearBottom(el) {
    try {
      return (el.scrollHeight - el.clientHeight - el.scrollTop) <= STICKY_THRESHOLD;
    } catch (e) {
      return true;
    }
  }

  function scrollToBottom(el) {
    // Use RAF twice to allow layout after mutations
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        try {
          el.scrollTop = el.scrollHeight;
        } catch (e) { /* no-op */ }
      });
    });
  }

  function attachObserver(el) {
    if (!el || el.__scrollBottomObserverAttached) return;
    el.__scrollBottomObserverAttached = true;

    // Initial snap to bottom on first load
    scrollToBottom(el);

    // Track user intent: if they scroll far up, we won't auto-stick
    var userNearBottom = true;
    el.addEventListener("scroll", function () {
      userNearBottom = isNearBottom(el);
    }, { passive: true });

    var mo = new MutationObserver(function (mutations) {
      var appended = false;
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.type === "childList" && (m.addedNodes && m.addedNodes.length)) {
          appended = true;
          break;
        }
      }
      if (appended && userNearBottom) {
        scrollToBottom(el);
      }
    });

    mo.observe(el, { childList: true, subtree: false });
  }

  function init() {
    var nodes = document.querySelectorAll('[data-scroll-bottom="true"]');
    for (var i = 0; i < nodes.length; i++) {
      attachObserver(nodes[i]);
    }

    // Optional: listen for a generic custom event in case pages already dispatch one
    window.addEventListener("ikta:notes:appended", function () {
      for (var j = 0; j < nodes.length; j++) {
        // Force scroll if event explicitly says new note was appended
        scrollToBottom(nodes[j]);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();