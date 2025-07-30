import io
from app.models import User, Case, db
from tests.helpers import create_user, login

def test_protected_routes_require_login(client):
    resp = client.get('/dashboard')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    resp = client.get('/cases/new')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_admin_access_admin_routes(client, app):
    with app.app_context():
        create_user('admin1', 'pw', 'admin')
        case = Case(case_number='A1')
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, 'admin1', 'pw')
        assert client.get('/admin/users').status_code == 200
        assert client.get('/admin/cases').status_code == 200
        # assignment routes restricted to szignáló in code
        resp = client.get('/szignal_cases')
        assert resp.status_code == 403

def test_iroda_permissions(client, app):
    with app.app_context():
        create_user('office', 'pw', 'iroda')
        case = Case(case_number='I1')
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, 'office', 'pw')
        assert client.get('/cases/new').status_code == 200
        data = {'file': (io.BytesIO(b'x'), 'test.txt'), 'category': 'egyéb'}
        resp = client.post(f'/cases/{cid}/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 302
        # forbidden actions
        assert client.get('/admin/users').status_code == 403
        assert client.post(f'/admin/cases/{cid}/delete').status_code == 403
        assert client.get('/szignal_cases').status_code == 403


def test_szakerto_permissions(client, app):
    with app.app_context():
        create_user('doc', 'pw', 'szakértő')
        case = Case(case_number='S1', expert_1='doc')
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, 'doc', 'pw')
        # access own case execution view
        assert client.get(f'/ugyeim/{cid}/elvegzem').status_code == 200
        # cannot access admin or assignment routes
        assert client.get('/admin/users').status_code == 403
        assert client.get('/szignal_cases').status_code == 403

