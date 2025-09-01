from app.models import User, db
from tests.helpers import create_user, login


def test_add_user_with_full_name(client, app):
    with app.app_context():
        admin = create_user("admin", "secret", role="admin")
    with client:
        login(client, "admin", "secret")
        resp = client.post(
            "/admin/users/add",
            data={
                "username": "alice",
                "password": "pw",
                "role": "iroda",
                "screen_name": "Alice S.",
                "full_name": "Alice Smith",
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)
    with app.app_context():
        u = User.query.filter_by(username="alice").one()
        assert u.full_name == "Alice Smith"
        assert u.screen_name == "Alice S."


def test_edit_user_updates_full_name(client, app):
    with app.app_context():
        admin = create_user("admin", "secret", role="admin")
        u = create_user("bob", "pw", role="leíró")
        uid = u.id
    with client:
        login(client, "admin", "secret")
        resp = client.post(
            f"/admin/users/{uid}/edit",
            data={
                "username": "bob",
                "role": "leíró",
                "screen_name": "Bobby",
                "full_name": "Bob Builder",
            },
            follow_redirects=True,
        )
        assert resp.status_code in (200, 302)
    with app.app_context():
        u2 = db.session.get(User, uid)
        assert u2.full_name == "Bob Builder"
        assert u2.screen_name == "Bobby"
