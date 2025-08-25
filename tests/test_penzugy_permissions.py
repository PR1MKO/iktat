from datetime import date

import pytest

from app import db
from app.models import Case
from app.investigations.models import Investigation
from tests.helpers import create_user, login, create_investigation
from app.utils.time_utils import now_local


def _setup_records():
    case = Case(case_number='B:1001/2025', deceased_name='Teszt', deadline=now_local(), birth_date=date(2000, 1, 1))
    db.session.add(case)
    inv = create_investigation()
    db.session.commit()
    return case, inv


def test_penzugy_read_only_views_and_posts(client, app):
    with app.app_context():
        create_user('fin', 'pw', role='pénzügy')
        case, inv = _setup_records()
        cid, iid = case.id, inv.id
        orig_name = case.deceased_name
        orig_subj = inv.subject_name
    with client:
        login(client, 'fin', 'pw')
        resp = client.get('/cases')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        for forbidden in ['Szerkeszt', 'Hozzáadás']:
            assert forbidden not in text
        resp = client.get(f'/cases/{cid}')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        for forbidden in ['Szerkeszt', 'Hozzárendel']:
            assert forbidden not in text
        resp = client.get('/investigations/')
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert 'Szerkeszt' not in text
        resp = client.post(f'/cases/{cid}/edit', data={'deceased_name': 'Változtat'})
        assert resp.status_code in (302, 403)
        resp = client.post(f'/investigations/{iid}/edit', data={'subject_name': 'Változtat'})
        assert resp.status_code in (302, 403)
    with app.app_context():
        assert db.session.get(Case, cid).deceased_name == orig_name
        assert db.session.get(Investigation, iid).subject_name == orig_subj


@pytest.mark.parametrize(
    'role, endpoint',
    [
        ('admin', '/admin/users'),
        ('iroda', '/cases/new'),
        ('szignáló', '/dashboard'),
        ('szakértő', '/dashboard'),
        ('leíró', '/dashboard'),
        ('toxi', '/ugyeim/toxi'),
    ],
)
def test_other_roles_retained_actions(client, app, role, endpoint):
    with app.app_context():
        create_user(role, 'pw', role=role)
    with client:
        login(client, role, 'pw')
        resp = client.get(endpoint)
        assert resp.status_code in (200, 302)