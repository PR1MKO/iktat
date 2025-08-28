from flask_login import login_required
from app.utils.roles import roles_required

def require_roles(*roles):
    # Thin alias to keep a single import point; semantics unchanged.
    return roles_required(*roles)