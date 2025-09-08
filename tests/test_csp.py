import re


def test_login_has_csp(client):
    resp = client.get("/login")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp
    html = resp.get_data(as_text=True)
    assert re.search(r"\son[a-zA-Z]+\s*=", html) is None
    scripts = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", html)
    for attrs in scripts:
        assert 'type="application/json"' in attrs and 'id="page-data"' in attrs
