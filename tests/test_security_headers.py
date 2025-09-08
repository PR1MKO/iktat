from tests.helpers import create_user, login, login_follow

EXPECTED_HEADERS = {
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def test_security_headers_present(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self' 'nonce-" in csp
    assert "'unsafe-inline'" not in csp
    for key, value in EXPECTED_HEADERS.items():
        assert resp.headers.get(key) == value
    assert "Strict-Transport-Security" not in resp.headers

    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    resp = client.get("/")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self' 'nonce-" in csp
    assert "'unsafe-inline'" not in csp
    for key, value in EXPECTED_HEADERS.items():
        assert resp.headers.get(key) == value


def test_hsts_when_https(app, client):
    app.config["PREFERRED_URL_SCHEME"] = "https"
    resp = client.get("/login")
    assert (
        resp.headers.get("Strict-Transport-Security")
        == "max-age=15552000; includeSubDomains"
    )


def test_session_cookie_flags(client):
    create_user("admin", "secret", "admin")
    resp = login(client, "admin", "secret")
    cookie = resp.headers.get("Set-Cookie", "")
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_cookie_notice_flow(client):
    create_user("user", "pass", "admin")
    resp = login_follow(client, "user", "pass")
    assert b'id="cookie-banner"' in resp.data
    resp = client.post("/ack_cookie_notice", headers={"X-CSRFToken": "token"})
    assert resp.status_code == 204
    resp = client.get("/dashboard")
    assert b'id="cookie-banner"' not in resp.data
