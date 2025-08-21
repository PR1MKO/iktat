# tests/conftest.py

import os
import sys

import pytest
from sqlalchemy.pool import StaticPool

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from config import TestingConfig  # noqa: E402

# --- Ensure all models are registered before create_all() ---
from app import models as core_models  # noqa: F401
from app.investigations import models as inv_models  # noqa: F401
# ------------------------------------------------------------


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    # Shared in‑memory DB across the process for deterministic tests
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,                  # allow login form posts in tests
        SQLALCHEMY_DATABASE_URI="sqlite://",     # shared in‑memory DB
        SQLALCHEMY_BINDS={                       # second bind for investigations
            "examination": "sqlite://",
        },
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        SQLALCHEMY_SESSION_OPTIONS={
            "expire_on_commit": False,           # avoid mid‑request reloads
        },
    )

    # Optional guard: fail fast if someone changes this in the future
    assert app.config["SQLALCHEMY_SESSION_OPTIONS"]["expire_on_commit"] is False

    with app.app_context():
        # Schema setup is handled per-test in the _db fixture below.
        yield app

    # No file cleanup needed — using in‑memory DBs.


# Create a fresh schema for all binds before each test (Option A: db.create_all)
@pytest.fixture(autouse=True)
def _db(app):
    with app.app_context():
        # Default bind
        db.drop_all()
        db.create_all()

        # Extra binds (e.g., "examination")
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            db.drop_all(bind_key=bind_key)
            db.create_all(bind_key=bind_key)

        yield

        # Teardown between tests
        db.session.remove()
        try:
            db.drop_all()
            for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
                db.drop_all(bind_key=bind_key)
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


# ------------------------------------------------------------
# Option B (reference only): Run Alembic migrations instead of create_all
#   Slower; closer to production. Uncomment to use.
#
# from alembic import command
# from alembic.config import Config as AlembicConfig
#
# @pytest.fixture(autouse=True)
# def _db_with_migrations(app):
#     with app.app_context():
#         alembic_cfg = AlembicConfig("migrations/alembic.ini")
#         command.downgrade(alembic_cfg, "base")
#         command.upgrade(alembic_cfg, "head")
#         yield
#         db.session.remove()
#         command.downgrade(alembic_cfg, "base")
# ------------------------------------------------------------
