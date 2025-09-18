import io

import pytest

from app import db
from app.investigations.models import Investigation
from tests.helpers import create_investigation, create_user, login


@pytest.fixture
def make_investigation_with_assignment(app):
    def _make(**kwargs):
        with app.app_context():
            inv = create_investigation(**kwargs)
            assigned_users = {
                "szak": create_user("assigned_szak", "secret", "szak"),
                "leir": create_user("assigned_leir", "secret", "leir"),
                "toxi": create_user("assigned_toxi", "secret", "toxi"),
            }
            inv.expert1_id = assigned_users["szak"].id
            inv.expert2_id = assigned_users["toxi"].id
            inv.describer_id = assigned_users["leir"].id
            db.session.commit()
            return inv, assigned_users

    return _make


@pytest.fixture
def login_as_role(app, client):
    def _login(role, *, assigned_to=None, assigned_users=None):
        username = f"{role}_{'assigned' if assigned_to else 'user'}"
        with app.app_context():
            user = None
            if assigned_to and assigned_users:
                user = assigned_users.get(role)
            if user is None:
                user = create_user(username, "secret", role)
            if assigned_to:
                inv = db.session.get(Investigation, assigned_to.id)
                if inv is None:
                    raise AssertionError("Investigation not found for assignment")
                if role in {"szak", "szakértő"}:
                    inv.expert1_id = user.id
                elif role in {"leir", "leíró"}:
                    inv.describer_id = user.id
                elif role == "toxi":
                    inv.expert2_id = user.id
                db.session.commit()
        login(client, user.username, "secret")
        return user

    return _login


@pytest.mark.parametrize(
    "role,assigned,expect_ok",
    [
        ("admin", False, True),
        ("iroda", False, True),
        ("szig", False, True),
        ("penz", False, True),
        ("szak", True, True),
        ("szak", False, False),
        ("leir", True, True),
        ("leir", False, False),
        ("toxi", True, True),
        ("toxi", False, False),
    ],
)
def test_upload_policy_matrix(
    client,
    make_investigation_with_assignment,
    login_as_role,
    role,
    assigned,
    expect_ok,
):
    inv, assigned_users = make_investigation_with_assignment()
    login_as_role(
        role,
        assigned_to=inv if assigned else None,
        assigned_users=assigned_users,
    )
    data = {"category": "documents", "file": (io.BytesIO(b"x"), "a.txt")}
    resp = client.post(
        f"/investigations/{inv.id}/upload",
        data=data,
        content_type="multipart/form-data",
    )
    if expect_ok:
        assert resp.status_code in (200, 201, 302)
    else:
        assert resp.status_code == 403
