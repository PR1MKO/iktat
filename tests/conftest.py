import os
import sys
import tempfile

import pytest

# Ensure the examination database uses an isolated temporary file during tests
fd, EXAM_DB_PATH = tempfile.mkstemp(prefix="exam_test", suffix=".db")
os.close(fd)
os.environ["EXAMINATION_DATABASE_URL"] = f"sqlite:///{EXAM_DB_PATH}"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from config import TestingConfig

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        db.create_all(bind_key="examination")
        yield app
        db.session.remove()
        db.drop_all()
        db.drop_all(bind_key="examination")
    test_db = os.path.join(app.instance_path, 'test.db')
    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(EXAM_DB_PATH):
        os.remove(EXAM_DB_PATH)

@pytest.fixture
def client(app):
    return app.test_client()

