"""Utilities for presenting user names consistently."""

from __future__ import annotations

from typing import Any, Optional


def user_display_name(user: Optional[Any], *, default: str = "system") -> str:
    """Return the preferred display name for *user* with fallbacks."""

    if not user:
        return default
    try:
        for attr in ("full_name", "screen_name", "username"):
            value = getattr(user, attr, None)
            if value:
                return value
    except Exception:  # pragma: no cover - defensive for LocalProxy edge cases
        pass
    return default
