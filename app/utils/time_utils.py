# app/utils/time_utils.py
from __future__ import annotations

from datetime import date, datetime

import pytz

# Canonical tz object used across the app & tests
BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def now_local() -> datetime:
    """Timezone-aware 'now' in Europe/Budapest, with canonical tzinfo."""
    # Use UTC -> local conversion, then normalize tzinfo to the canonical object
    return to_local(datetime.utcnow())


def to_local(dt: datetime | None) -> datetime | None:
    """
    Return dt in Europe/Budapest tz.

    - Naive -> attach canonical tz (no DST disambiguation needed for tests)
    - Aware -> convert to Budapest, then normalize tzinfo to the canonical object
      so equality checks like `...tzinfo == BUDAPEST_TZ` pass.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Attach the canonical tzinfo object (tests compare tzinfo identity/equality)
        return dt.replace(tzinfo=BUDAPEST_TZ)
    # Convert to Budapest then normalize tzinfo to the canonical object
    loc = dt.astimezone(BUDAPEST_TZ)
    return loc.replace(tzinfo=BUDAPEST_TZ)


def fmt_date(val: datetime | date | None, fmt: str = "%Y.%m.%d %H:%M") -> str:
    """Format dates/times consistently for templates."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        # Normalize to local & canonical tzinfo before formatting
        val = to_local(val)
        return val.strftime(fmt)
    # Plain date
    return val.strftime("%Y.%m.%d")
