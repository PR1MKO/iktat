import pytest

from app.models import User, db
from tests.helpers import create_user, login


def test_add_expert_requires_default_leiro(client, app):
    with app.app_context():
        admin = create_user('admin', 'secret', role='admin')
        leiro = create_user('leiro1', 'pw', role='leíró')
    with client:
        login(client, 'admin', 'secret')
        resp = client.post('/admin/users/add', data={
            'username': 'docx', 'password': 'pw', 'role': 'szakértő',
        }, follow_redirects=True)
        assert any(r.status_code == 302 for r in resp.history)
        assert b'k\xc3\xb6telez' in resp.data.lower() or b'kotelez' in resp.data.lower()


def test_add_expert_persists_default_leiro(client, app):
    with app.app_context():
        admin = create_user('admin', 'secret', role='admin')
        leiro = create_user('leiro2', 'pw', role='leíró')
        leiro_id = leiro.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.post('/admin/users/add', data={
            'username': 'doc2', 'password': 'pw', 'role': 'szakértő',
            'default_leiro_id': str(leiro_id),
        }, follow_redirects=True)
        assert resp.status_code in (200, 302)
    with app.app_context():
        u = User.query.filter_by(username='doc2').one()
        assert u.role == 'szakértő'
        assert u.default_leiro_id == leiro_id


def test_add_non_expert_ignores_default_leiro(client, app):
    with app.app_context():
        admin = create_user('admin', 'secret', role='admin')
        leiro = create_user('leiro3', 'pw', role='leíró')
        leiro_id = leiro.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.post('/admin/users/add', data={
            'username': 'writer1', 'password': 'pw', 'role': 'leíró',
            'default_leiro_id': str(leiro_id),
        }, follow_redirects=True)
        assert resp.status_code in (200, 302)
    with app.app_context():
        u = User.query.filter_by(username='writer1').one()
        assert u.role == 'leíró'
        assert u.default_leiro_id is None


def test_edit_expert_updates_default_leiro(client, app):
    with app.app_context():
        admin = create_user('admin', 'secret', role='admin')
        leiroA = create_user('leiroA', 'pw', role='leíró')
        leiroB = create_user('leiroB', 'pw', role='leíró')
        expert = create_user('docE', 'pw', role='szakértő')
        expert.default_leiro_id = leiroA.id
        db.session.commit()
        eid = expert.id
        leiroB_id = leiroB.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.post(f'/admin/users/{eid}/edit', data={
            'username': 'docE', 'role': 'szakértő', 'default_leiro_id': str(leiroB_id),
        }, follow_redirects=True)
        assert resp.status_code in (200, 302)
    with app.app_context():
        u = db.session.get(User, eid)
        assert u.default_leiro_id == leiroB_id
		