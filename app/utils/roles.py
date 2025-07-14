from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*roles):
    """Decorator to ensure the current user has one of the given roles."""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return wrapper