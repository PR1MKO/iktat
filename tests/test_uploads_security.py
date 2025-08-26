from io import BytesIO
from pathlib import Path

from app import db
from app.models import Case
from tests.helpers import create_user, login


def _setup_roots(app, tmp_path):
    cases = tmp_path / "cases"
    inv = tmp_path / "investigations"
    cases.mkdir()
    inv.mkdir()
    app.config["UPLOAD_CASES_ROOT"] = cases
    app.config["CASE_UPLOAD_FOLDER"] = str(cases)
    app.config["UPLOAD_INVESTIGATIONS_ROOT"] = inv
    app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(inv)


def test_upload_traversal_blocked(app, client, tmp_path):
    _setup_roots(app, tmp_path)
    with app.app_context():
        case = Case(case_number="T1")
        db.session.add(case)
        db.session.commit()
        cid = case.id
        create_user(role="admin")
    login(client, "admin", "secret")
    data = {
        "category": "egyéb",
        "file": (BytesIO(b"x"), "../../evil.txt"),
    }
    resp = client.post(
        f"/cases/{cid}/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


def test_download_traversal_blocked(app, client, tmp_path):
    _setup_roots(app, tmp_path)
    with app.app_context():
        case = Case(case_number="D1")
        db.session.add(case)
        db.session.commit()
        cid = case.id
        create_user(role="admin")
    login(client, "admin", "secret")
    resp = client.get(f"/cases/{cid}/files/../secret.txt")
    assert resp.status_code == 400


def test_extension_whitelist(app, client, tmp_path):
    _setup_roots(app, tmp_path)
    with app.app_context():
        case = Case(case_number="E1")
        db.session.add(case)
        db.session.commit()
        cid = case.id
        create_user(role="admin")
    login(client, "admin", "secret")
    data = {
        "category": "egyéb",
        "file": (BytesIO(b"data"), "bad.exe"),
    }
    resp = client.post(
        f"/cases/{cid}/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code >= 400