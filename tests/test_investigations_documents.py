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
