"""
tests/compat_flaskwtf.py
Test-only shim: if flask_wtf Recaptcha widgets import Markup from Flask (1.1.x),
patch them to use markupsafe.Markup so pytest can run in Codex envs pinning 1.1.1.
Safe to import multiple times; no effect if already fixed in >=1.2.x.
"""

from importlib import import_module

try:
    # Import the Recaptcha widgets module which is where the bad import lives in <=1.1.x
    widgets = import_module("flask_wtf.recaptcha.widgets")
    # If it exposes a Markup symbol coming via Flask, swap it to markupsafe.Markup.
    try:
        from markupsafe import Markup as _SafeMarkup

        # Rebind only if needed
        if getattr(widgets, "Markup", None) and widgets.Markup.__module__ in {
            "flask",
            "flask.helpers",
        }:
            widgets.Markup = _SafeMarkup  # type: ignore[attr-defined]
    except Exception:
        # If markupsafe isn't available or anything odd happens, fail silently (tests may still run).
        pass
except Exception:
    # If flask_wtf.recaptcha isn't present, no-op.
    pass
