import re
from pathlib import Path


def test_base_includes_alerts_js_after_bootstrap():
    html = Path("app/templates/base.html").read_text(encoding="utf-8")
    # bootstrap.bundle.js should appear before alerts.js
    boot = re.search(r'src="[^"]*bootstrap[^\"]*bundle[^\"]*\.js"', html)
    alerts = re.search(
        r'src="\{\{\s*url_for\(\s*[\'\"]static[\'\"],\s*filename\s*=\s*[\'\"]js/alerts\.js[\'\"]\s*\)\s*\}\}"',
        html,
    )
    assert boot is not None, "bootstrap.bundle.js not found in base.html"
    assert alerts is not None, "alerts.js not included in base.html"
    assert (
        boot.start() < alerts.start()
    ), "alerts.js must load after bootstrap.bundle.js"


def test_no_inline_alert_timer_anywhere():
    patterns = [r"setTimeout\s*\(", r"bootstrap\.Alert\.getOrCreateInstance\("]
    # Inline timer should NOT appear inside templates; allowed only in external JS
    base_text = Path("app/templates/base.html").read_text(encoding="utf-8")
    assert "js/alerts.js" in base_text
    for tpl in Path("app/templates").rglob("*.html"):
        text = tpl.read_text(encoding="utf-8")
        assert not re.search(
            patterns[0], text
        ), f"Inline setTimeout found in template {tpl}"
        # Allow Alert usage only in JS file, not inline:
        assert (
            "bootstrap.Alert.getOrCreateInstance(" not in text
        ), f"Inline Bootstrap Alert usage in {tpl}"


def test_alerts_js_has_timer_and_close_logic():
    js = Path("app/static/js/alerts.js").read_text(encoding="utf-8")
    assert "setTimeout" in js, "alerts.js must implement a dismissal timer"
    # Either Bootstrap close path or fallback removal must exist:
    assert (
        "bootstrap.Alert.getOrCreateInstance" in js
        or "el.classList.remove('show')" in js
    )
