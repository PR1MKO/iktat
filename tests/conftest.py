# tests/conftest.py

import os
import sys
import tempfile

import pytest

# Use an isolated temp SQLite file for the 'examination' bind during tests
fd, EXAM_DB_FD_PATH = tempfile.mkstemp(prefix="exam_test_", suffix=".db")
os.close(fd)
os.environ["EXAMINATION_DATABASE_URL"] = f"sqlite:///{EXAM_DB_FD_PATH}"

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db  # noqa: E402
from config import TestingConfig  # noqa: E402


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        # Create all tables for both the default and 'examination' binds
        db.create_all()
        db.create_all(bind_key="examination")

        yield app

        # Teardown: drop all and fully dispose engines to release file handles (Windows)
        db.session.remove()
        db.drop_all()
        db.drop_all(bind_key="examination")

        # Dispose engines while still in app context
        try:
            db.get_engine(app).dispose()
        except Exception:
            pass
        try:
            db.get_engine(app, bind="examination").dispose()
        except Exception:
            pass

    # Remove the default test DB file if present
    test_db = os.path.join(app.instance_path, "test.db")
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except PermissionError:
            # Last-ditch: try again after a dispose (in case anything held on)
            try:
                db.get_engine(app).dispose()
            except Exception:
                pass
            try:
                os.remove(test_db)
            except Exception:
                pass

    # Remove the temporary examination DB file
    if os.path.exists(EXAM_DB_FD_PATH):
        try:
            os.remove(EXAM_DB_FD_PATH)
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()
