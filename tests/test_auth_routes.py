import pytest
from flask import session

from app.models import User, db
from tests.helpers import create_user, login

# --- Login Tests ---

def test_login_form_renders(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'name="username"' in resp.data


def test_login_success(client, app):
    with app.app_context():
        create_user()
    with client:
        resp = login(client, 'admin', 'secret')
        assert resp.status_code == 302
        assert '/dashboard' in resp.headers['Location']
        assert session.get('_user_id') is not None


def test_login_wrong_password(client, app):
    with app.app_context():
        create_user()
    resp = client.post('/login', data={'username': 'admin', 'password': 'wrong'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid username or password' in resp.data


def test_login_unknown_user(client):
    resp = client.post('/login', data={'username': 'nope', 'password': 'x'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid username or password' in resp.data


def test_logout_clears_session(client, app):
    with app.app_context():
        create_user()
    with client:
        login(client, 'admin', 'secret')
        resp = client.get('/logout')
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']
        assert session.get('_user_id') is None


# --- Registration via admin ---

def test_register_user_success(client, app):
    with app.app_context():
        create_user('root', 'rootpass', role='admin')
    with client:
        login(client, 'root', 'rootpass')
        resp = client.post('/admin/users/add', data={
            'username': 'newuser',
            'password': 'newpass',
            'role': 'admin'
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            u = User.query.filter_by(username='newuser').first()
            assert u is not None
            assert u.check_password('newpass')
            assert u.password_hash != 'newpass'


def test_register_missing_fields(client, app):
    with app.app_context():
        create_user('root', 'rootpass', role='admin')
    with client:
        login(client, 'root', 'rootpass')
        resp = client.post('/admin/users/add', data={
            'username': 'incomplete',
            'password': '',
            'role': 'admin'
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username='incomplete').first() is None


def test_register_duplicate_username(client, app):
    with app.app_context():
        create_user('root', 'rootpass', role='admin')
        create_user('dup', 'pw', role='admin')
    with client:
        login(client, 'root', 'rootpass')
        resp = client.post('/admin/users/add', data={
            'username': 'dup',
            'password': 'new',
            'role': 'admin'
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username='dup').count() == 1
            
