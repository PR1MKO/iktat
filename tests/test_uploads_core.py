import io
from pathlib import Path

import pytest

from app.models import Case, db
from app.paths import file_safe_case_number
from tests.helpers import create_user, login


@pytest.mark.uploads
def test_file_upload_succeeds_with_csrf(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number="U-1")
        db.session.add(case)
        db.session.commit()
        cid = case.id

    with client:
        login(client, "admin", "secret")
        data = {
            "file": (io.BytesIO(b"data"), "report.pdf"),
            "category": "egyéb",
        }
        resp = client.post(f"/cases/{cid}/upload", data=data)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith(f"/cases/{cid}")

    with app.app_context():
        safe = file_safe_case_number(case.case_number)
        dest = Path(app.config["UPLOAD_CASES_ROOT"]) / safe / "report.pdf"
        assert dest.exists()


@pytest.mark.uploads
def test_upload_rejected_without_csrf(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number="U-2")
        db.session.add(case)
        db.session.commit()
        cid = case.id

    with client:
        login(client, "admin", "secret")
        data = {"file": (io.BytesIO(b"x"), "file.pdf")}
        resp = client.post(f"/cases/{cid}/upload", data=data)
        assert resp.status_code == 302