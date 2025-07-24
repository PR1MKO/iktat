import pytz
from datetime import datetime

BUDAPEST_TZ = pytz.timezone("Europe/Budapest")


def now_local() -> datetime:
    """Return current time in Budapest timezone."""
    return datetime.now(BUDAPEST_TZ)
    
  