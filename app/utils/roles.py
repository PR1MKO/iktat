from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def roles_required(*roles):
    """Ensure the current user has one of the given roles."""

    roles = [r for r in roles if r]

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Bejelentkezés szükséges.", "warning")
                return redirect(url_for("auth.login"))
            if roles and current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator  
  