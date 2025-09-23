# app/utils/roles.py
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User  # adjust if your User model lives elsewhere

ROLE_CANON = {
    "admin": "admin",
    "iroda": "iroda",
    "szignáló": "szignáló",
    "szig": "szignáló",
    "pénzügy": "pénzügy",
    "penz": "pénzügy",
    "szakértő": "szakértő",
    "szak": "szakértő",
    "leíró": "leíró",
    "leir": "leíró",
    "lei": "leíró",
    "toxi": "toxi",
}


def canonical_role(role: str | None) -> str | None:
    """Map a stored/legacy role string to its canonical representation."""

    if role is None:
        return None
    if not isinstance(role, str):
        return role
    normalized = role.strip()
    if not normalized:
        return None
    return ROLE_CANON.get(normalized, normalized)


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
        if not user:
            return None
        return canonical_role(getattr(user, "role", None))
    except Exception:
        return None


def roles_required(*roles):
    """Ensure the current user has one of the given roles."""
    allowed_roles = {
        canon for canon in (canonical_role(r) for r in roles if r) if canon
    }

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Bejelentkezés szükséges.", "warning")
                return redirect(url_for("auth.login"))
            if allowed_roles:
                role = _resolve_role()
                if role not in allowed_roles:
                    abort(403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator
