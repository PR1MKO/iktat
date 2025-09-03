from tests.helpers import create_user, login


def test_csp_allows_bootstrap_icons_font_sources(client):
    r = client.get("/login")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "font-src" in csp
    assert "https://cdn.jsdelivr.net" in csp
    assert "https://cdnjs.cloudflare.com" in csp


def test_base_contains_bi_classes(client):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    r = client.get("/")
    html = r.get_data(as_text=True)
    assert 'class="bi bi-house-door"' in html or "bi-house-door" in html
