from datetime import datetime, timedelta
from app.models import db, Case, User
from app.audit import log_action
from app.email_utils import send_email

def auto_close_stale_cases():
    now = datetime.utcnow()

    # Consider all cases with a past deadline as stale
    stale_cases = Case.query.filter(Case.deadline < now).all()

    count = 0
    for case in stale_cases:
        if case.status != 'lejárt':
            old_status = case.status
            case.status = 'lejárt'
            log_action("Case auto-closed", f"{case.case_number}: {old_status} → lejárt")
            count += 1

    db.session.commit()
    return count

def send_deadline_warning_email():
    today = datetime.utcnow()
    upcoming = today + timedelta(days=14)

    cases_due = Case.query.filter(
        Case.deadline >= today,
        Case.deadline <= upcoming,
        Case.status != 'lezárva'
    ).order_by(Case.deadline).all()

    if not cases_due:
        return 0

    recipients = [user.username for user in User.query.filter(User.role.in_(['admin', 'igazgató'])).all()]
    if not recipients:
        return 0

    body = "Az alábbi ügyek 14 napon belül esedékesek:\n\n"
    for case in cases_due:
        body += f"- {case.case_number} – {case.deceased_name} – Határidő: {case.deadline.strftime('%Y-%m-%d %H:%M')}\n"

    send_email(
        subject="⚠ Határidő figyelmeztetés – Ügykezelő rendszer",
        recipients=recipients,
        body=body
    )

    return len(cases_due)

