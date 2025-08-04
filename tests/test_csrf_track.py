import re
import pytest
from tests.helpers import create_user
from app import db, create_app
from config import Config

class CSRFEnabledConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TRACK_USER_ACTIVITY = True

@pytest.fixture
def app_csrf():
    app = create_app(CSRFEnabledConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client_csrf(app_csrf):
    return app_csrf.test_client()

def extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, 'CSRF token not found in HTML'
    return match.group(1)

def test_track_route_csrf_exempt(client_csrf, app_csrf):
    with app_csrf.app_context():
        create_user('u1', 'pw')

    # login with CSRF token
    res = client_csrf.get('/login')
    token = extract_csrf_token(res.data.decode())
    login_resp = client_csrf.post('/login', data={'username': 'u1', 'password': 'pw', 'csrf_token': token})
    assert login_resp.status_code in (302, 303)

    # post to /track without CSRF token
    resp = client_csrf.post('/track', json={'event_type': 'click'})
    assert resp.status_code == 204

    # posting to another route without CSRF should fail
    bad_resp = client_csrf.post('/login', data={'username': 'u1', 'password': 'pw'})
    assert bad_resp.status_code == 400