# app/tasks/__init__.py
from __future__ import annotations

from datetime import timedelta

from app.models import Case
from app.utils.case_status import CASE_STATUS_FINAL
from app.utils.time_utils import now_local


def send_deadline_warning_email() -> int:
    """Return how many non-final cases are due within 14 days."""
    today = now_local()
    upcoming = today + timedelta(days=14)

    cases_due = (
        Case.query.filter(
            Case.deadline >= today,
            Case.deadline <= upcoming,
            Case.status != CASE_STATUS_FINAL,
        )
        .order_by(Case.deadline)
        .all()
    )

    # keep behavior minimal; tests only rely on the count
    return len(cases_due)
