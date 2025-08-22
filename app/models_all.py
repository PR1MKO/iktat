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

# --- Core/domain models (single default bind) ------------------------------
# These define tables like: user, case, change_log, uploaded_file, etc.
from app.models import *  # noqa: F401,F403

# --- Investigations feature models -----------------------------------------
# These define: Investigation, InvestigationNote, InvestigationAttachment,
# InvestigationChangeLog, etc. (default bind unless a model sets __bind_key__).
from app.investigations.models import *  # noqa: F401,F403

# --- Optional: any additional model packages -------------------------------
# If you later add modules with models (e.g., examination/other binds),
# import them here so tests pick them up with create_all().
try:
    from app.examination.models import *  # type: ignore  # noqa: F401,F403
except Exception:
    # Silently ignore if the optional package doesn't exist in this install.
    pass
