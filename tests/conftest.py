import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from config import TestingConfig

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    test_db = os.path.join(app.instance_path, 'test.db')
    if os.path.exists(test_db):
        os.remove(test_db)

@pytest.fixture
def client(app):
    return app.test_client()

