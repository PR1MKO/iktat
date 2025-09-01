# app/utils/__init__.py
"""
Utilities package export hub.

We explicitly import the submodules we want to expose so that:
    from app.utils import dates
works reliably in tests and app code.

If something goes wrong on import (e.g. a typo or circular import),
we raise a clear ImportError so the root cause shows up in pytest output.
"""

from importlib import import_module

__all__ = ["dates", "time_utils"]


def _import_submodule(name: str):
    try:
        return import_module(f".{name}", __name__)
    except Exception as exc:
        # Make the failure obvious and attributable to the real cause.
        raise ImportError(f"Failed to import app.utils.{name}: {exc}") from exc


# Import and export submodules as attributes of app.utils
dates = _import_submodule("dates")
time_utils = _import_submodule("time_utils")
