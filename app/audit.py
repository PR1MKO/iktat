from .models import db, AuditLog
from app.utils.time_utils import now_local
from flask_login import current_user
from flask import current_app, flash, has_request_context

def log_action(action: str, details: str = None):
    if not current_user.is_authenticated:
        return  # Skip logging if no user is logged in

    log_entry = AuditLog(
        timestamp=now_local(),
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action=action,
        details=details
    )
    db.session.add(log_entry)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        if has_request_context():
            flash("Valami hiba történt. Próbáld újra.", "danger")

 