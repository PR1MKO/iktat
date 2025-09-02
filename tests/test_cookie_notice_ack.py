from tests.helpers import create_user, login_follow


def test_no_inline_cookie_handler(client, app):
    with app.app_context():
        create_user("user", "pass", "admin")
        script_url = "/static/js/cookie_notice.js"
    with client:
        resp = login_follow(client, "user", "pass")
        html = resp.get_data(as_text=True)
        assert 'id="cookie-banner"' in html
        assert script_url in html
        assert 'fetch("/ack_cookie_notice"' not in html
        resp = client.post("/ack_cookie_notice", headers={"X-CSRFToken": "token"})
        assert resp.status_code == 204
        resp = client.get("/dashboard")
        html = resp.get_data(as_text=True)
        assert 'id="cookie-banner"' not in html
        assert script_url not in html


def test_ack_cookie_requires_auth(client):
    resp = client.post("/ack_cookie_notice", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")
