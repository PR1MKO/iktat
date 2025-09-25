# --- Imports first to satisfy E402 ---
import itertools
import os
import pathlib
import pathlib as _p
import random
import shutil
import sys
import uuid
from datetime import datetime, timezone

import flask as _fl
import pytest
from markupsafe import Markup as _MSM
from sqlalchemy.pool import StaticPool

# tests/conftest.py


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


@pytest.fixture(scope="session", autouse=True)
def _force_tmp_upload_roots(tmp_path_factory):
    """Route all upload roots to pytest tmp dirs, preventing writes to real instance/."""

    tmp_base = tmp_path_factory.mktemp("uploads")
    tmp_cases = tmp_base / "uploads_cases"
    tmp_investigations = tmp_base / "uploads_investigations"
    tmp_cases.mkdir(parents=True, exist_ok=True)
    tmp_investigations.mkdir(parents=True, exist_ok=True)

    from flask import current_app

    import app.paths as _paths

    orig_case_root = getattr(_paths, "case_root", None)
    orig_investigation_root = getattr(_paths, "investigation_root", None)
    orig_default_case = (
        getattr(_paths, "_default_case_root", None)
        if hasattr(_paths, "_default_case_root")
        else None
    )
    orig_default_investigation = (
        getattr(_paths, "_default_investigation_root", None)
        if hasattr(_paths, "_default_investigation_root")
        else None
    )

    def _resolve_app():
        try:
            return current_app._get_current_object()
        except Exception:  # pragma: no cover - happens outside app context
            return None

    def _case_root_override():
        app_obj = _resolve_app()
        default_target = tmp_cases
        if app_obj is not None:
            cfg_value = app_obj.config.get("CASE_UPLOAD_FOLDER") or app_obj.config.get(
                "UPLOAD_CASES_ROOT"
            )
            if cfg_value:
                cfg_path = pathlib.Path(cfg_value)
                if orig_default_case is not None:
                    try:
                        default_orig = orig_default_case()
                    except Exception:
                        default_orig = None
                else:
                    default_orig = None
                if default_orig is not None and cfg_path == default_orig:
                    root = default_target
                else:
                    root = cfg_path
            else:
                root = default_target

            app_obj.config["CASE_UPLOAD_FOLDER"] = str(root)
            app_obj.config["UPLOAD_CASES_ROOT"] = str(root)
        else:
            root = default_target

        root.mkdir(parents=True, exist_ok=True)
        return root

    def _investigation_root_override():
        app_obj = _resolve_app()
        default_target = tmp_investigations
        if app_obj is not None:
            cfg_value = app_obj.config.get(
                "INVESTIGATION_UPLOAD_FOLDER"
            ) or app_obj.config.get("UPLOAD_INVESTIGATIONS_ROOT")
            if cfg_value:
                cfg_path = pathlib.Path(cfg_value)
                if orig_default_investigation is not None:
                    try:
                        default_orig = orig_default_investigation()
                    except Exception:
                        default_orig = None
                else:
                    default_orig = None
                if default_orig is not None and cfg_path == default_orig:
                    root = default_target
                else:
                    root = cfg_path
            else:
                root = default_target

            app_obj.config["INVESTIGATION_UPLOAD_FOLDER"] = str(root)
            app_obj.config["UPLOAD_INVESTIGATIONS_ROOT"] = str(root)
        else:
            root = default_target

        root.mkdir(parents=True, exist_ok=True)
        return root

    def _default_case_root_override():
        tmp_cases.mkdir(parents=True, exist_ok=True)
        return tmp_cases

    def _default_investigation_root_override():
        tmp_investigations.mkdir(parents=True, exist_ok=True)
        return tmp_investigations

    _paths.case_root = _case_root_override
    _paths.investigation_root = _investigation_root_override
    if orig_default_case is not None:
        _paths._default_case_root = _default_case_root_override
    if orig_default_investigation is not None:
        _paths._default_investigation_root = _default_investigation_root_override

    os.environ["UPLOAD_CASES_ROOT"] = str(tmp_cases)
    os.environ["UPLOAD_INVESTIGATIONS_ROOT"] = str(tmp_investigations)

    try:
        yield
    finally:
        if orig_case_root is not None:
            _paths.case_root = orig_case_root
        if orig_investigation_root is not None:
            _paths.investigation_root = orig_investigation_root
        if orig_default_case is not None:
            _paths._default_case_root = orig_default_case
        if orig_default_investigation is not None:
            _paths._default_investigation_root = orig_default_investigation

        try:
            shutil.rmtree(tmp_base, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _seed_random(monkeypatch):
    random.seed(1337)
    counter = itertools.count()
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=next(counter)))


@pytest.fixture(autouse=True)
def _fixed_now(monkeypatch):
    fixed = datetime(2020, 1, 1, 12, 0, tzinfo=time_utils.BUDAPEST_TZ)
    fixed_utc = fixed.astimezone(timezone.utc)
    monkeypatch.setattr(time_utils, "now_local", lambda: fixed)
    monkeypatch.setattr(time_utils, "now_utc", lambda: fixed_utc)
    monkeypatch.setattr(dates_util, "now_utc", lambda: fixed_utc)
    for name, mod in list(sys.modules.items()):
        if name.startswith("tests."):
            if hasattr(mod, "now_local"):
                monkeypatch.setattr(mod, "now_local", lambda: fixed, raising=False)
            if hasattr(mod, "now_utc"):
                monkeypatch.setattr(mod, "now_utc", lambda: fixed_utc, raising=False)


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    # Shared in-memory DB across the process for deterministic tests
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # allow login form posts in tests
        SQLALCHEMY_DATABASE_URI="sqlite://",  # shared in-memory DB
        SQLALCHEMY_BINDS={  # second bind for 'examination' etc.
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

    assert app.config["SQLALCHEMY_SESSION_OPTIONS"]["expire_on_commit"] is False

    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def _db(app):
    """
    HARD RESET schema for all binds before each test (drop -> create).
    Prevents 'table already exists' / 'no such table' issues and clears
    stale identity maps — using modern Flask-SQLAlchemy engine accessors.
    """
    with app.app_context():
        # Clean up any open session first
        try:
            db.session.remove()
        except Exception:
            pass

        # Drop default bind
        try:
            db.drop_all()
        except Exception:
            pass

        # Drop each extra bind
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            try:
                db.drop_all(bind_key=bind_key)
            except Exception:
                pass

        # Recreate default bind
        db.create_all()

        # Recreate each extra bind
        for bind_key in app.config.get("SQLALCHEMY_BINDS", {}):
            db.create_all(bind_key=bind_key)

        # Ensure no expired attributes will reload mid-request
        db.session.expire_all()

        yield

        # Post-test cleanup; next test will drop/create again
        try:
            db.session.remove()
        finally:
            # Dispose all engines without using deprecated get_engine
            try:
                db.engine.dispose()
            except Exception:
                pass
            for eng in getattr(db, "engines", {}).values():
                try:
                    eng.dispose()
                except Exception:
                    pass


@pytest.fixture
def client(app):
    return app.test_client()
