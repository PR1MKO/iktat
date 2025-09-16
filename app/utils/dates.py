from datetime import date, datetime, timezone
from typing import Dict, Optional

from app.utils.time_utils import HUMAN_TIME_FMT, fmt_budapest, to_budapest


def now_utc() -> datetime:  # pragma: no cover - thin wrapper for monkeypatching
    return datetime.now(timezone.utc)


def safe_fmt(dt: Optional[datetime], pattern: str = HUMAN_TIME_FMT) -> str:
    if not dt:
        return ""
    try:
        return fmt_budapest(dt, pattern)
    except Exception:
        return dt.strftime(pattern)


def safe_iso(dt: Optional[datetime]) -> str:
    return dt.isoformat() if dt else ""


def compute_deadline_flags(
    deadline: Optional[datetime], warn_days: int = 7
) -> Dict[str, object]:
    if not deadline:
        return {
            "is_expired": False,
            "is_today": False,
            "is_warning": False,
            "days_left": None,
        }
    try:
        today = to_budapest(now_utc()).date()
        d = to_budapest(deadline).date()
    except Exception:
        today = date.today()
        d = deadline.date()
    days_left = (d - today).days
    return {
        "is_expired": days_left < 0,
        "is_today": days_left == 0,
        "is_warning": 0 <= days_left <= warn_days,
        "days_left": days_left,
    }


def attach_case_dates(case):
    case.registration_time_str = safe_fmt(getattr(case, "registration_time", None))
    case.deadline_str = safe_fmt(getattr(case, "deadline", None))
    case.updated_at_iso = safe_iso(getattr(case, "updated_at", None))
    case.deadline_flags = compute_deadline_flags(getattr(case, "deadline", None))
    case.tox_viewed_at_str = safe_fmt(getattr(case, "tox_viewed_at", None))
    case.tox_doc_generated_at_str = safe_fmt(
        getattr(case, "tox_doc_generated_at", None)
    )
    if hasattr(case, "uploaded_file_records"):
        for rec in case.uploaded_file_records:
            rec.upload_time_str = safe_fmt(getattr(rec, "upload_time", None))
    return case
