from typing import Optional

from app import db
from app.models import User


def get_user_safe(user_id: int) -> Optional[User]:
    """Read-only fetch of a core User by id. Returns None if not found."""
    if not user_id:
        return None
    # Use the core (default) bind/session
    return db.session.get(User, user_id)
