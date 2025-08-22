import re

from app.models import User
from tests.helpers import create_user, login

def test_add_user_page_shows_penugy(client, app):
    with app.app_context():
        create_user('admin', 'secret', role='admin')
    with client:
        login(client, 'admin', 'secret')
        resp = client.get('/admin/users/add')
        assert resp.status_code == 200
        assert 'Pénzügy' in resp.get_data(as_text=True)

def test_create_user_with_penugy_role(client, app):
    with app.app_context():
        create_user('admin', 'secret', role='admin')
    with client:
        login(client, 'admin', 'secret')
        resp = client.post(
            '/admin/users/add',
            data={'username': 'fin', 'password': 'pw', 'role': 'pénzügy'},
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)
    with app.app_context():
        u = User.query.filter_by(username='fin').one()
        assert u.role == 'pénzügy'

def test_edit_user_shows_penugy_selected(client, app):
    with app.app_context():
        create_user('admin', 'secret', role='admin')
        u = create_user('fin2', 'pw', role='pénzügy')
        uid = u.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.get(f'/admin/users/{uid}/edit')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'selected value="pénzügy"' in html
		