from datetime import date, datetime

import pytz

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def now_local() -> datetime:
    """Return current time in Budapest timezone."""
    return datetime.now(BUDAPEST_TZ)


def to_local(dt: datetime) -> datetime:
    """Ensure ``dt`` is in Budapest timezone.

    If ``dt`` is timezone-aware, convert it. If it's naive, attach
    ``BUDAPEST_TZ`` without altering the clock time.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BUDAPEST_TZ)
    return dt.astimezone(BUDAPEST_TZ)


def fmt_date(value: date | datetime | None) -> str:
    """Format a date or datetime as YYYY.MM.DD."""
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%Y.%m.%d")
