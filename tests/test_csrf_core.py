import pytest
from flask_wtf.csrf import generate_csrf

from tests.helpers import create_user, login


@pytest.mark.csrf
def test_cookie_notice_csrf(client, app):
    with app.app_context():
        create_user()
    with client:
        login(client, "admin", "secret")
        app.config["WTF_CSRF_ENABLED"] = True
        # Banner visible before acknowledgement
        page = client.get("/dashboard")
        assert b"cookie-banner" in page.data
        resp = client.post("/ack_cookie_notice")
        assert resp.status_code == 400
        token = generate_csrf()
        resp = client.post("/ack_cookie_notice", data={"csrf_token": token})
        assert resp.status_code == 204
        page = client.get("/dashboard")
        assert b"cookie-banner" not in page.data
