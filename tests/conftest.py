# tests/conftest.py

# --- Imports first to satisfy E402 ---
import itertools
import os
import pathlib
import random
import sys
import uuid
from datetime import datetime, timezone

import flask as _fl
import pytest
from markupsafe import Markup as _MSM
from sqlalchemy.pool import StaticPool

# --- Test-only fix for Flask-WTF<=1.1.x Markup import ---
_fl.Markup = _MSM  # ensure any "from flask import Markup" resolves safely
import tests.compat_flaskwtf  # noqa: F401

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SECRET_KEY", "test-secret")

# --- Ensure *all* models are registered before create_all() ---
from app import models_all  # noqa: F401
from app import create_app, db
from app.utils import dates as dates_util
from app.utils import time_utils
from config import TestingConfig

# --------------------------------------------------------------


@pytest.fixture(autouse=True, scope="session")
def _force_utf8_read_text():
    """Ensure Path.read_text defaults to UTF-8 and restore after tests."""
    orig = pathlib.Path.read_text

    def _read_text_utf8(self, *args, **kwargs):
        kwargs.setdefault("encoding", "utf-8")
        return orig(self, *args, **kwargs)

    pathlib.Path.read_text = _read_text_utf8
    try:
        yield
    finally:
        pathlib.Path.read_text = orig


@pytest.fixture(autouse=True)
def _seed_random(monkeypatch):
    random.seed(1337)
    counter = itertools.count()
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=next(counter)))


@pytest.fixture(autouse=True)
def _fixed_now(monkeypatch):
    fixed = time_utils.BUDAPEST_TZ.localize(datetime(2020, 1, 1, 12, 0))
    monkeypatch.setattr(time_utils, "now_local", lambda: fixed)
    monkeypatch.setattr(dates_util, "now_utc", lambda: fixed.astimezone(timezone.utc))
    for name, mod in list(sys.modules.items()):
        if name.startswith("tests.") and hasattr(mod, "now_local"):
            monkeypatch.setattr(mod, "now_local", lambda: fixed, raising=False)


@pytest.fixture(autouse=True)
def _tmp_upload_dirs(tmp_path, monkeypatch):
    cases = tmp_path / "uploads_cases"
    investigations = tmp_path / "uploads_investigations"
    cases.mkdir()
    investigations.mkdir()
    monkeypatch.setenv("UPLOAD_CASES_ROOT", str(cases))
    monkeypatch.setenv("UPLOAD_INVESTIGATIONS_ROOT", str(investigations))


@pytest.fixture
def app(_tmp_upload_dirs):
    app = create_app(TestingConfig)

    # Shared in-memory DB across the process for deterministic tests
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # allow login form posts in tests
        SQLALCHEMY_DATABASE_URI="sqlite://",  # shared in-memory DB
        SQLALCHEMY_BINDS={  # second bind (example) for investigations/others
            "examination": "sqlite://",
        },
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        SQLALCHEMY_SESSION_OPTIONS={
            "expire_on_commit": False,  # avoid mid-request reloads
        },
    )

    # Optional guard: fail fast if someone changes this in the future
    assert app.config["SQLALCHEMY_SESSION_OPTIONS"]["expire_on_commit"] is False

    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def _db(app):
    """
    Fresh schema for all binds before each test.
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
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            try:
                db.drop_all(bind_key=bind_key)
            except Exception:
                pass
        try:
            db.drop_all()
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()
