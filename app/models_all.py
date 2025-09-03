# app/models_all.py
"""
Aggregate/registration module for all SQLAlchemy models.

Why this exists:
- During tests we call `db.create_all()` against a fresh in-memory DB.
- SQLAlchemy only creates tables for models that have been imported
  (i.e., registered in the current declarative metadata).
- Importing this module ensures every model is imported once so that
  `db.create_all()` can see all tables.

This module does NOT declare new models. It only imports existing ones.
Import order can matter if there are inter-module relationships, so keep
core models first, then feature/blueprint models.
"""

from app import db  # noqa: F401  # ensure the extension is initialized

# --- Investigations feature models (bind='examination' via __bind_key__) ---
from app.investigations.models import *  # noqa: F401,F403

# --- Core/domain models (single default bind) ------------------------------
from app.models import *  # noqa: F401,F403

# --- Optional: any additional model packages -------------------------------
try:
    from app.examination.models import *  # type: ignore  # noqa: F401,F403
except Exception:
    # Silently ignore if the optional package doesn't exist in this install.
    pass
