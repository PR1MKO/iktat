import io

import pytest

from app import db
from app.investigations.models import InvestigationAttachment
from tests.helpers import create_investigation, create_user, login


@pytest.mark.usefixtures("app")
def test_documents_page_renders_with_attachment(client, app):
    with app.app_context():
        user = create_user("admin", "pw", "admin")
        login(client, "admin", "pw")
        inv = create_investigation(subject_name="T", investigation_type="type1")
        att = InvestigationAttachment(
            investigation_id=inv.id,
            filename="demo.txt",
            category="egyeb",
            uploaded_by=user.id,
        )
        db.session.add(att)
        db.session.commit()

        resp = client.get(f"/investigations/{inv.id}/documents")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert f"/investigations/{inv.id}/download/{att.id}" in html


@pytest.mark.usefixtures("app")
def test_upload_redirects_to_documents_without_500(client, app):
    with app.app_context():
        create_user("iro", "pw", "iroda")
        login(client, "iro", "pw")
        inv = create_investigation(subject_name="T", investigation_type="type1")
        data = {
            "file": (io.BytesIO(b"hello"), "hello.txt"),
            "category": "egyeb",
        }

        resp = client.post(
            f"/investigations/{inv.id}/upload",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "Fájl feltöltve" in resp.get_data(as_text=True)


@pytest.mark.usefixtures("app")
def test_download_uses_investigation_root_when_constants_differ(client, app, tmp_path):
    storage_root = tmp_path / "investigation-storage"
    storage_root.mkdir()
    legacy_root = tmp_path / "legacy-storage"

    with app.app_context():
        app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(storage_root)
        app.config["UPLOAD_INVESTIGATIONS_ROOT"] = str(legacy_root)

        user = create_user("leiro_worker", "pw", "leíró")
        inv = create_investigation(subject_name="X", investigation_type="type2")
        inv.describer_id = user.id
        db.session.commit()
        inv_id = inv.id
        username = user.username

    login(client, username, "pw")
    upload_resp = client.post(
        f"/investigations/{inv_id}/upload",
        data={
            "file": (io.BytesIO(b"download-ok"), "doc.pdf"),
            "category": "jegyzőkönyv",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert upload_resp.status_code in {302, 303}

    with app.app_context():
        attachment = (
            InvestigationAttachment.query.filter_by(investigation_id=inv_id)
            .order_by(InvestigationAttachment.id.desc())
            .first()
        )

    assert attachment is not None

    download_resp = client.get(f"/investigations/{inv_id}/download/{attachment.id}")
    assert download_resp.status_code == 200
    assert download_resp.data == b"download-ok"
    assert "attachment" in download_resp.headers.get("Content-Disposition", "")

    missing_resp = client.get(
        f"/investigations/{inv_id}/download/{attachment.id + 9999}"
    )
    assert missing_resp.status_code == 404
