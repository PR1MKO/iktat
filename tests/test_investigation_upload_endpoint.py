import io
import re
from pathlib import Path

import pytest

from app.investigations.models import InvestigationAttachment
from app.paths import ensure_investigation_folder
from tests.helpers import create_investigation, create_user, login


def _post_upload(client, inv_id, data, **kwargs):
    return client.post(
        f"/investigations/{inv_id}/upload",
        data=data,
        content_type="multipart/form-data",
        **kwargs,
    )


def test_upload_allows_szignal_when_assigned(client, app):
    with app.app_context():
        signer = create_user("signer", "secret", "szignáló")
        inv = create_investigation(expert1_id=signer.id)
        inv_id = inv.id
        case_number = inv.case_number

    login(client, "signer", "secret")
    data = {"category": "végzés", "file": (io.BytesIO(b"data"), "doc.pdf")}
    resp = _post_upload(client, inv_id, data)
    assert resp.status_code in (302, 303)

    with app.app_context():
        attachments = InvestigationAttachment.query.filter_by(
            investigation_id=inv_id
        ).all()
        assert len(attachments) == 1
        att = attachments[0]
        assert att.category == "végzés"
        assert att.uploaded_by == signer.id
        upload_dir = Path(ensure_investigation_folder(case_number))
        assert (upload_dir / att.filename).exists()


@pytest.mark.parametrize(
    "role, assign_self",
    [
        ("admin", False),
        ("iroda", False),
        ("szakértő", True),
    ],
)
def test_upload_allows_existing_roles(client, app, role, assign_self):
    username = f"user_{role}"
    with app.app_context():
        user = create_user(username, "secret", role)
        inv_kwargs = {"case_number": f"CASE-{role}"}
        if assign_self:
            inv_kwargs["expert1_id"] = user.id
        inv = create_investigation(**inv_kwargs)
        inv_id = inv.id

    login(client, username, "secret")
    data = {"category": "jegyzőkönyv", "file": (io.BytesIO(b"ok"), "file.pdf")}
    resp = _post_upload(client, inv_id, data)
    assert resp.status_code in (302, 303)

    with app.app_context():
        saved = InvestigationAttachment.query.filter_by(investigation_id=inv_id).all()
        assert len(saved) == 1
        assert saved[0].uploaded_by == user.id


def test_upload_rejects_disallowed_role(client, app):
    with app.app_context():
        create_user("viewer", "secret", "leíró")
        inv = create_investigation()

    login(client, "viewer", "secret")
    data = {"category": "végzés", "file": (io.BytesIO(b"data"), "doc.pdf")}
    resp = _post_upload(client, inv.id, data)
    assert resp.status_code == 403


def test_upload_invalid_payload_returns_400_for_ajax(client, app):
    with app.app_context():
        admin = create_user("admin", "secret", "admin")
        inv = create_investigation()

    login(client, "admin", "secret")
    data = {"category": "", "file": (io.BytesIO(b""), "")}
    resp = _post_upload(
        client,
        inv.id,
        data,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload == {"error": "invalid"}

    with app.app_context():
        assert (
            InvestigationAttachment.query.filter_by(investigation_id=inv.id).count()
            == 0
        )


def test_upload_requires_csrf_token_when_enabled(client, app):
    with app.app_context():
        signer = create_user("signer", "secret", "szignáló")
        inv = create_investigation(expert1_id=signer.id)
        inv_id = inv.id

    login(client, "signer", "secret")

    with app.app_context():
        original_csrf = app.config.get("WTF_CSRF_ENABLED", False)
        app.config["WTF_CSRF_ENABLED"] = True

    try:
        assign_resp = client.get(f"/investigations/{inv_id}/assign")
        assert assign_resp.status_code == 200
        html = assign_resp.get_data(as_text=True)
        token_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        assert token_match is not None
        token = token_match.group(1)

        bad_data = {"category": "végzés", "file": (io.BytesIO(b"one"), "a.pdf")}
        bad_resp = _post_upload(client, inv_id, bad_data)
        assert bad_resp.status_code == 400

        good_data = {
            "category": "végzés",
            "csrf_token": token,
            "file": (io.BytesIO(b"two"), "b.pdf"),
        }
        good_resp = _post_upload(client, inv_id, good_data)
        assert good_resp.status_code in (302, 303)

        with app.app_context():
            count = InvestigationAttachment.query.filter_by(
                investigation_id=inv_id
            ).count()
            assert count == 1
    finally:
        with app.app_context():
            app.config["WTF_CSRF_ENABLED"] = original_csrf
