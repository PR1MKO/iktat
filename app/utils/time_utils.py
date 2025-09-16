# app/utils/time_utils.py
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

# Canonical tz object and human-friendly format
HUMAN_TIME_FMT = "%Y/%m/%d %H:%M"
BUDAPEST_TZ = ZoneInfo("Europe/Budapest")


def now_utc() -> datetime:
    """Timezone-aware UTC now for storage."""
    return datetime.now(timezone.utc)


def to_budapest(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Treat naive values as UTC by policy
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BUDAPEST_TZ)


def fmt_budapest(dt: datetime | None, fmt: str = HUMAN_TIME_FMT) -> str:
    dt_loc = to_budapest(dt)
    return dt_loc.strftime(fmt) if dt_loc else "–"


# Deprecated helpers ---------------------------------------------------------
def now_local() -> datetime:
    """Legacy helper for code still expecting Budapest-local now."""
    return to_budapest(now_utc())


def to_local(dt: datetime | None) -> datetime | None:  # pragma: no cover - shim
    """Backward-compatible alias for :func:`to_budapest`."""
    return to_budapest(dt)


def fmt_date(val: datetime | date | None, fmt: str = HUMAN_TIME_FMT) -> str:
    """Format dates/times consistently for templates."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return fmt_budapest(val, fmt)
    # Plain date
    return val.strftime("%Y.%m.%d")
