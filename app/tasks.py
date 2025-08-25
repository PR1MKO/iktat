from datetime import timedelta
from app.models import db, Case, User
from app.utils.time_utils import BUDAPEST_TZ, now_local
from app.utils.case_status import CASE_STATUS_FINAL
from app.audit import log_action
from app.email_utils import send_email

def send_deadline_warning_email():
    today = now_local()
    upcoming = today + timedelta(days=14)

    cases_due = Case.query.filter(
        Case.deadline >= today,
        Case.deadline <= upcoming,
        Case.status != CASE_STATUS_FINAL
    ).order_by(Case.deadline).all()

    if not cases_due:
        return 0

    recipients = [user.username for user in User.query.filter(User.role.in_(['admin', 'igazgató'])).all()]
    if not recipients:
        return 0

    body = "Az alábbi ügyek 14 napon belül esedékesek:\n\n"
    for case in cases_due:
        if case.deadline:
            dt = case.deadline
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=BUDAPEST_TZ)
            formatted = dt.astimezone(BUDAPEST_TZ).strftime('%Y-%m-%d %H:%M')
        else:
            formatted = 'N/A'
        body += f"- {case.case_number} – {case.deceased_name} – Határidő: {formatted}\n"

    send_email(
        subject="⚠ Határidő figyelmeztetés – Ügykezelő rendszer",
        recipients=recipients,
        body=body
    )

    return len(cases_due)

