from pathlib import Path

import pytest

from app.models import Case, UploadedFile, db
from app.paths import ensure_case_folder
from tests.helpers import create_user, login


@pytest.mark.routes
def test_route_smoke(client, app):
    assert client.get("/login").status_code == 200
    assert client.get("/dashboard").status_code == 302

    with app.app_context():
        create_user()
        case = Case(case_number="R2")
        db.session.add(case)
        db.session.commit()
        cid = case.id
        upload_dir = ensure_case_folder(case.case_number)
        file_path = Path(upload_dir) / "ok.txt"
        file_path.write_text("ok", encoding="utf-8")
        db.session.add(
            UploadedFile(
                case_id=cid,
                filename="ok.txt",
                uploader="admin",
                category="egyéb",
            )
        )
        db.session.commit()

    with client:
        login(client, "admin", "secret")
        assert client.get("/cases").status_code == 200
        assert client.get(f"/cases/{cid+1}/view").status_code == 404
        assert client.get(f"/cases/{cid}/files/ok.txt").status_code == 200
        assert client.get(f"/cases/{cid}/files/missing.txt").status_code == 404
