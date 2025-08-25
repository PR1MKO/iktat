import pytest
from tests.helpers import create_user, login


def test_no_store_header_added(client):
    create_user('admin', 'secret', 'admin')
    login(client, 'admin', 'secret')
    resp = client.get('/dashboard')
    cc = resp.headers.get('Cache-Control', '')
    assert 'no-store' in cc
    assert resp.headers.get('Pragma') == 'no-cache'
    assert resp.headers.get('Expires') == '0'


def test_no_store_header_disabled(app, client):
    app.config['NO_STORE_HEADERS_ENABLED'] = False
    create_user('admin', 'secret', 'admin')
    login(client, 'admin', 'secret')
    resp = client.get('/dashboard')
    cc = resp.headers.get('Cache-Control', '')
    assert 'no-store' not in cc
    assert 'Pragma' not in resp.headers
    assert 'Expires' not in resp.headers