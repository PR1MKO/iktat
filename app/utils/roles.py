# app/utils/roles.py
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm.exc import DetachedInstanceError, ObjectDeletedError

from app import db
from app.models import User  # adjust if your User model lives elsewhere


def _resolve_role():
    """Return the role for the current user, reloading if the SA instance is detached."""
    try:
        role = getattr(current_user, "role", None)
        if role is not None:
            return role
    except (DetachedInstanceError, ObjectDeletedError):
        # Fall through to fresh load
        pass

    # Fallback: fetch a fresh instance by id
    uid = None
    try:
        uid = current_user.get_id()
    except Exception:
        uid = getattr(current_user, "id", None)

    if uid is None:
        return None

    try:
        key = int(uid) if isinstance(uid, str) and uid.isdigit() else uid
        user = db.session.get(User, key)
        return getattr(user, "role", None) if user else None
    except Exception:
        return None


def roles_required(*roles):
    """Ensure the current user has one of the given roles."""
    roles = [r for r in roles if r]

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            # Extra safety + user feedback (login_required also handles redirect)
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
