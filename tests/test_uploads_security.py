from io import BytesIO
from pathlib import Path

import pytest

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


def _prep_case(app, client, tmp_path, number):
    _setup_roots(app, tmp_path)
    with app.app_context():
        case = Case(case_number=number)
        db.session.add(case)
        db.session.commit()
        cid = case.id
        create_user(role="admin")
    login(client, "admin", "secret")
    return cid


def test_upload_traversal_blocked(app, client, tmp_path):
    cid = _prep_case(app, client, tmp_path, "T1")
    data = {"category": "egyéb", "file": (BytesIO(b"x"), "../../evil.txt")}
    resp = client.post(
        f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 400


def test_download_traversal_blocked(app, client, tmp_path):
    cid = _prep_case(app, client, tmp_path, "D1")
    resp = client.get(f"/cases/{cid}/files/../secret.txt")
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "fname, expected",
    [("bad.exe", False), ("good.pdf", True)],
)
def test_extension_whitelist(app, client, tmp_path, fname, expected):
    cid = _prep_case(app, client, tmp_path, "E1")
    data = {"category": "egyéb", "file": (BytesIO(b"data"), fname)}
    resp = client.post(
        f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
    )
    if expected:
        assert resp.status_code in (200, 302)
    else:
        assert resp.status_code >= 400


def test_mime_sanity(app, client, tmp_path):
    cid = _prep_case(app, client, tmp_path, "M1")
    data = {"category": "egyéb", "file": (BytesIO(b"pdf"), "a.pdf")}
    resp = client.post(
        f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code in (200, 302)
    resp = client.get(f"/cases/{cid}/files/a.pdf")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] in (
        "application/pdf",
        "application/octet-stream",
    )


def test_separate_roots(app, client, tmp_path):
    cid = _prep_case(app, client, tmp_path, "S1")
    fname = "root.pdf"
    data = {"category": "egyéb", "file": (BytesIO(b"data"), fname)}
    resp = client.post(
        f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code in (200, 302)
    assert not list(Path(app.config["UPLOAD_INVESTIGATIONS_ROOT"]).rglob(fname))


def test_size_limit(app, client, tmp_path):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    cid = _prep_case(app, client, tmp_path, "L1")
    big = BytesIO(b"x" * 2048)
    data = {"category": "egyéb", "file": (big, "big.pdf")}
    resp = client.post(
        f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
    )
    assert resp.status_code == 413
