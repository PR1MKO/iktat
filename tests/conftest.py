# tests/conftest.py
# --- Test-only fix for Flask-WTF<=1.1.x Markup import ---
import tests.compat_flaskwtf  # noqa: F401
# --------------------------------------------------------
import os
import sys

import pytest
from sqlalchemy.pool import StaticPool

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from config import TestingConfig  # noqa: E402

# --- Ensure *all* models are registered before create_all() ---
# Single import that aggregates every model module.
from app import models_all  # noqa: F401  # pylint: disable=unused-import
# --------------------------------------------------------------


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    # Shared in-memory DB across the process for deterministic tests
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,                  # allow login form posts in tests
        SQLALCHEMY_DATABASE_URI="sqlite://",     # shared in-memory DB
        SQLALCHEMY_BINDS={                       # second bind (example) for investigations/others
            "examination": "sqlite://",
        },
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        SQLALCHEMY_SESSION_OPTIONS={
            "expire_on_commit": False,           # avoid mid-request reloads
        },
    )

    # Optional guard: fail fast if someone changes this in the future
    assert app.config["SQLALCHEMY_SESSION_OPTIONS"]["expire_on_commit"] is False

    with app.app_context():
        # Schema setup/teardown handled by the _db fixture below.
        yield app


@pytest.fixture(autouse=True)
def _db(app):
    """
    Fresh schema for all binds before each test.

    Important: we *don't* call drop_all() before create_all(), because on a
    brand-new in-memory SQLite DB, dropping non-existent tables can throw
    OperationalError in some environments. We drop in teardown instead.
    """
    with app.app_context():
        # Create default bind schema
        db.create_all()

        # Create schemas for extra binds (e.g., "examination")
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            db.create_all(bind_key=bind_key)

        yield

        # Teardown between tests
        db.session.remove()
        # Drop extra binds first (isolate any relationships)
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            try:
                db.drop_all(bind_key=bind_key)
            except Exception:
                # Some engines/versions can race on checkfirst; ignore here.
                pass
        try:
            db.drop_all()
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()
