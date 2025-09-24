import io

import pytest

from app import db
from app.investigations.models import Investigation, InvestigationAttachment
from app.utils.roles import canonical_role
from tests.helpers import (
    create_investigation,
    create_investigation_with_default_leiro,
    create_user,
    login,
)


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


@pytest.mark.parametrize(
    "role,assigned,expect_ok",
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


def test_default_leiro_upload_and_download_roundtrip(app, client):
    with app.app_context():
        inv, leiro, _ = create_investigation_with_default_leiro()
        inv_id = inv.id
        username = leiro.username

    login(client, username, "secret")

    data = {"category": "jegyzőkönyv", "file": (io.BytesIO(b"data"), "proof.pdf")}
    resp = client.post(
        f"/investigations/{inv_id}/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code in (200, 201, 302)

    with app.app_context():
        attachment = (
            InvestigationAttachment.query.filter_by(investigation_id=inv_id)
            .order_by(InvestigationAttachment.id.desc())
            .first()
        )
        assert attachment is not None
        attachment_id = attachment.id

    download = client.get(f"/investigations/{inv_id}/download/{attachment_id}")
    assert download.status_code == 200
