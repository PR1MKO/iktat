import pytz
from datetime import datetime, date

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def now_local() -> datetime:
    """Return current time in Budapest timezone."""
    return datetime.now(BUDAPEST_TZ)
    
def fmt_date(value: date | datetime | None) -> str:
    """Format a date or datetime as YYYY.MM.DD."""
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%Y.%m.%d")
    
