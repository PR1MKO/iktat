from flask import session

from app.models import User, db
from tests.helpers import create_user, login

# --- Login Tests ---


def test_login_form_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b'name="username"' in resp.data


def test_login_success(client, app):
    with app.app_context():
        create_user()
    with client:
        resp = login(client, "admin", "secret")
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]
        assert session.get("_user_id") is not None


def test_login_wrong_password(client, app):
    with app.app_context():
        create_user()
    resp = client.post(
        "/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_login_unknown_user(client):
    resp = client.post(
        "/login", data={"username": "nope", "password": "x"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_logout_clears_session(client, app):
    with app.app_context():
        create_user()
    with client:
        login(client, "admin", "secret")
        resp = client.get("/logout")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        assert session.get("_user_id") is None


# --- Registration via admin ---


def test_register_user_success(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
    with client:
        login(client, "root", "rootpass")
        resp = client.post(
            "/admin/users/add",
            data={"username": "newuser", "password": "newpass", "role": "admin"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            u = User.query.filter_by(username="newuser").first()
            assert u is not None
            assert u.check_password("newpass")
            assert u.password_hash != "newpass"


def test_register_missing_fields(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
    with client:
        login(client, "root", "rootpass")
        resp = client.post(
            "/admin/users/add",
            data={"username": "incomplete", "password": "", "role": "admin"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username="incomplete").first() is None


def test_register_duplicate_username(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
        create_user("dup", "pw", role="admin")
    with client:
        login(client, "root", "rootpass")
        resp = client.post(
            "/admin/users/add",
            data={"username": "dup", "password": "new", "role": "admin"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert User.query.filter_by(username="dup").count() == 1


def test_edit_user_dropdown_shown_for_szakerto(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
        create_user("leiro1", "pw", role="leíró")
        sz = create_user("doc", "pw", role="szakértő")
        sz_id = sz.id
    with client:
        login(client, "root", "rootpass")
        resp = client.get(f"/admin/users/{sz_id}/edit")
        assert resp.status_code == 200
        assert b"Default le\xc3\xadr\xc3\xb3" in resp.data


def test_edit_user_dropdown_not_shown_for_admin(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
        user = create_user("usr", "pw", role="admin")
        user_id = user.id
    with client:
        login(client, "root", "rootpass")
        resp = client.get(f"/admin/users/{user_id}/edit")
        assert resp.status_code == 200
        assert b"Default le\xc3\xadr\xc3\xb3" in resp.data
        assert b"disabled" in resp.data


def test_edit_user_sets_default_leiro(client, app):
    with app.app_context():
        create_user("root", "rootpass", role="admin")
        leiro = create_user("leiro1", "pw", role="leíró")
        sz = create_user("doc", "pw", role="szakértő")
        sz_id = sz.id
        leiro_id = leiro.id
    with client:
        login(client, "root", "rootpass")
        resp = client.post(
            f"/admin/users/{sz_id}/edit",
            data={
                "username": "doc",
                "role": "szakértő",
                "screen_name": "",
                "default_leiro_id": str(leiro_id),
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            updated = db.session.get(User, sz_id)
            assert updated.default_leiro_id == leiro_id
