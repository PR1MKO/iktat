from tests.helpers import create_investigation, create_user, login


def test_investigation_expert_name_display(client, app):
    with app.app_context():
        admin = create_user(username="admin", password="secret", role="admin")
        expert = create_user(username="expert", role="szakértő")
        create_investigation(expert1_id=expert.id)
    login(client, "admin", "secret")
    resp = client.get("/investigations/")
    assert resp.status_code == 200
    assert b"expert" in resp.data


def test_missing_expert_shows_dash(client, app):
    with app.app_context():
        admin = create_user(username="admin", password="secret", role="admin")
        create_investigation(expert1_id=9999)
    login(client, "admin", "secret")
    resp = client.get("/investigations/")
    assert resp.status_code == 200
    assert "—".encode("utf-8") in resp.data
