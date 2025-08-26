import re
from pathlib import Path

import pytest
from flask_wtf.csrf import generate_csrf

from app.models import Case, db
from app.utils.time_utils import now_local
from tests.helpers import create_user


def _get_token(client, url):
    html = client.get(url).get_data(as_text=True)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "csrf token not found"
    return m.group(1)


def _create_case():
    case = Case(case_number='C100', registration_time=now_local(), status='beérkezett')
    db.session.add(case)
    db.session.commit()
    return case.id


def test_meta_token_present(client, app):
    app.config['WTF_CSRF_ENABLED'] = True
    resp = client.get('/login')
    html = resp.get_data(as_text=True)
    m = re.search(r'<meta name="csrf-token" content="([^"]+)">', html)
    assert m and m.group(1)


def test_ajax_header_rule_present():
    base_html = Path('app/templates/base.html').read_text(encoding='utf-8')
    assert 'X-CSRFToken' in base_html


@pytest.mark.parametrize('mode', ['login', 'add_note'])
def test_post_requires_token(client, app, mode):
    app.config['WTF_CSRF_ENABLED'] = True
    with client:
        if mode == 'login':
            url = '/login'
            resp = client.post(url, data={'username': 'x', 'password': 'y'})
            assert resp.status_code == 400
            token = _get_token(client, url)
            resp = client.post(url, data={'username': 'x', 'password': 'y', 'csrf_token': token})
            assert resp.status_code in (200, 302)
        else:
            with app.app_context():
                create_user('admin', 'pw', 'admin')
                case_id = _create_case()
            token = _get_token(client, '/login')
            resp = client.post('/login', data={'username': 'admin', 'password': 'pw', 'csrf_token': token})
            assert resp.status_code in (200, 302)
            url = f'/cases/{case_id}/add_note'
            resp = client.post(url, json={'new_note': 'hi'})
            assert resp.status_code == 400
            token = generate_csrf()
            resp = client.post(url, json={'new_note': 'hi'}, headers={'X-CSRFToken': token})
            assert resp.status_code == 200