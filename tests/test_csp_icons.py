from tests.helpers import create_user, login


def test_csp_contains_nonce(client):
    r = client.get("/login")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "script-src 'self' 'nonce-" in csp
    assert "'unsafe-inline'" not in csp


def test_base_contains_bi_classes(client):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    r = client.get("/")
    html = r.get_data(as_text=True)
    assert 'class="bi bi-house-door"' in html or "bi-house-door" in html
