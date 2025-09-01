# app/utils/roles.py
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User  # adjust if your User model lives elsewhere


def _resolve_role():
    """
    Return the role for the logged-in user **without** touching SA attributes
    on the session-bound current_user instance. Always reload by PK.
    """
    try:
        uid = current_user.get_id()
    except Exception:
        return None
    if not uid:
        return None
    try:
        key = int(uid) if isinstance(uid, str) and uid.isdigit() else uid
        user = db.session.get(User, key)
        return user.role if user else None
    except Exception:
        return None


def roles_required(*roles):
    """Ensure the current user has one of the given roles."""
    roles = [r for r in roles if r]

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Bejelentkezés szükséges.", "warning")
                return redirect(url_for("auth.login"))

            if roles:
                role = _resolve_role()
                if role not in roles:
                    abort(403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator
