import io

import pytest

from app import db
from app.investigations.models import Investigation
from app.utils.roles import canonical_role
from tests.helpers import create_investigation, create_user, login


@pytest.fixture
def make_investigation(app):
    def _make(**kwargs):
        with app.app_context():
            return create_investigation(**kwargs)

    return _make


@pytest.fixture
def make_investigation_with_assignment(app):
    def _make(**kwargs):
        with app.app_context():
            inv = create_investigation(**kwargs)
            roles = ["szak", "szakértő", "leir", "leíró", "toxi"]
            assigned_users = {}
            for idx, role in enumerate(roles):
                assigned_users[role] = create_user(f"assigned_{idx}", "secret", role)

            inv.expert1_id = assigned_users["szakértő"].id
            inv.expert2_id = assigned_users["toxi"].id
            inv.describer_id = assigned_users["leíró"].id
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
                user = assigned_users.get(role) or assigned_users.get(
                    canonical_role(role)
                )
            if user is None:
                user = create_user(username, "secret", role)
            if assigned_to:
                inv = db.session.get(Investigation, assigned_to.id)
                if inv is None:
                    raise AssertionError("Investigation not found for assignment")
                canon = canonical_role(role)
                if canon == "szakértő":
                    inv.expert1_id = user.id
                elif canon == "leíró":
                    inv.describer_id = user.id
                elif canon == "toxi":
                    inv.expert2_id = user.id
                db.session.commit()
        login(client, user.username, "secret")
        return user

    return _login


def test_admin_sees_upload_form_controls(client, app, make_investigation):
    with app.app_context():
        create_user("admin", "secret", "admin")
    inv = make_investigation()
    login(client, "admin", "secret")
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "-- Válasszon kategóriát --" in html
    assert "file-upload-form" in html
    assert "Csak a kijelölt" not in html


def test_investigations_upload_missing_category_rejected(
    client, app, make_investigation
):
    with app.app_context():
        create_user("admin", "secret", "admin")
    inv = make_investigation()
    login(client, "admin", "secret")
    data = {
        "category": "",
        "file": (io.BytesIO(b"%PDF-1.4"), "x.pdf"),
    }
    resp = client.post(
        f"/investigations/{inv.id}/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "Kategória megadása kötelező" in text


def test_unassigned_role_sees_info_alert(
    client, make_investigation_with_assignment, login_as_role
):
    inv, assigned_users = make_investigation_with_assignment()
    login_as_role("szak", assigned_users=assigned_users)
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "alert-info" in html
    assert "Csak a kijelölt szakértő vagy leíró tölthet fel a vizsgálathoz." in html
    assert "file-upload-form" not in html


def test_forbidden_upload_renders_styled_page(
    client, make_investigation_with_assignment, login_as_role
):
    inv, assigned_users = make_investigation_with_assignment()
    login_as_role("szak", assigned_users=assigned_users)
    resp = client.post(
        f"/investigations/{inv.id}/upload", data={}, follow_redirects=False
    )
    assert resp.status_code == 403
    html = resp.get_data(as_text=True)
    assert "Hozzáférés megtagadva" in html
    assert "Nincs jogosultság a kért művelethez." in html


@pytest.mark.parametrize(
    "role,assigned,expect_button",
    [
        ("admin", False, True),
        ("iroda", False, True),
        ("szignáló", False, True),
        ("szig", False, True),
        ("pénzügy", False, True),
        ("penz", False, True),
        ("szakértő", True, True),
        ("szakértő", False, False),
        ("szak", True, True),
        ("szak", False, False),
        ("leíró", True, True),
        ("leíró", False, False),
        ("leir", True, True),
        ("leir", False, False),
        ("toxi", True, True),
        ("toxi", False, False),
    ],
)
def test_upload_button_visibility(
    client,
    make_investigation_with_assignment,
    login_as_role,
    role,
    assigned,
    expect_button,
):
    inv, assigned_users = make_investigation_with_assignment()
    login_as_role(
        role,
        assigned_to=inv if assigned else None,
        assigned_users=assigned_users,
    )
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert ("file-upload-form" in html) == expect_button
    if not expect_button:
        assert "Csak a kijelölt szakértő vagy leíró tölthet fel a vizsgálathoz." in html
