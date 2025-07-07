from datetime import datetime
from .models import db, AuditLog
from flask_login import current_user

def log_action(action: str, details: str = None):
    if not current_user.is_authenticated:
        return  # Skip logging if no user is logged in

    log_entry = AuditLog(
        timestamp=datetime.utcnow(),
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action=action,
        details=details
    )
    db.session.add(log_entry)
    db.session.commit()
