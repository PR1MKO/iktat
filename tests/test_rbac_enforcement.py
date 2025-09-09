import pytest

from app.models import Case, db
from tests.helpers import create_investigation, create_user, login


@pytest.fixture
def setup(app):
    with app.app_context():
        case = Case(case_number="C1")
        db.session.add(case)
        db.session.commit()
        inv = create_investigation()
        roles = {
            "admin": "admin",
            "iroda": "iroda",
            "szak": "szakértő",
            "leiro": "leíró",
            "szignalo": "szignáló",
            "toxi": "toxi",
            "norole": "",
        }
        for username, role in roles.items():
            create_user(username, "pw", role)
        return {"case_id": case.id, "inv_id": inv.id}


def test_case_list_access(client, setup):
    resp = client.get("/cases")
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]
    with client:
        login(client, "norole", "pw")
        assert client.get("/cases").status_code == 403
    with client:
        login(client, "szak", "pw")
        assert client.get("/cases").status_code == 200


def test_case_detail_access(client, setup):
    cid = setup["case_id"]
    resp = client.get(f"/cases/{cid}")
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]
    with client:
        login(client, "norole", "pw")
        assert client.get(f"/cases/{cid}").status_code == 403
    with client:
        login(client, "iroda", "pw")
        assert client.get(f"/cases/{cid}").status_code == 200


def test_edit_basic_permissions(client, setup):
    cid = setup["case_id"]
    with client:
        login(client, "iroda", "pw")
        resp = client.post(f"/cases/{cid}/edit_basic", data={"deceased_name": "X"})
        assert resp.status_code in (200, 302)
    with client:
        login(client, "szak", "pw")
        assert client.post(f"/cases/{cid}/edit_basic", data={}).status_code == 403


def test_add_note_permissions(client, setup):
    cid = setup["case_id"]
    with client:
        login(client, "leiro", "pw")
        resp = client.post(f"/cases/{cid}/add_note", json={"new_note": "hi"})
        assert resp.status_code in (200, 302)
    with client:
        login(client, "norole", "pw")
        assert (
            client.post(f"/cases/{cid}/add_note", json={"new_note": "hi"}).status_code
            == 403
        )


def test_investigation_list_permissions(client, setup):
    with client:
        login(client, "szak", "pw")
        assert client.get("/investigations/").status_code == 200
    with client:
        login(client, "norole", "pw")
        assert client.get("/investigations/").status_code == 403


def test_investigation_note_permissions(client, setup):
    inv_id = setup["inv_id"]
    with client:
        login(client, "iroda", "pw")
        resp = client.post(f"/investigations/{inv_id}/notes", json={"text": "hi"})
        assert resp.status_code in (200, 302)
    with client:
        login(client, "szak", "pw")
        assert (
            client.post(
                f"/investigations/{inv_id}/notes", json={"text": "hi"}
            ).status_code
            == 403
        )


def test_investigation_list_allows_szignalo(client, setup):
    with client:
        login(client, "szignalo", "pw")
        assert client.get("/investigations/").status_code == 200


def test_investigation_view_allows_szignalo(client, setup):
    inv_id = setup["inv_id"]
    with client:
        login(client, "szignalo", "pw")
        assert client.get(f"/investigations/{inv_id}/view").status_code == 200


def test_investigation_documents_allows_szignalo(client, setup):
    inv_id = setup["inv_id"]
    with client:
        login(client, "szignalo", "pw")
        assert client.get(f"/investigations/{inv_id}/documents").status_code == 200


def test_investigation_posts_forbid_szignalo(client, setup):
    inv_id = setup["inv_id"]
    with client:
        login(client, "szignalo", "pw")
        assert client.post(f"/investigations/{inv_id}/edit", data={}).status_code == 403
        assert (
            client.post(
                f"/investigations/{inv_id}/notes", json={"text": "n/a"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/investigations/{inv_id}/upload",
                data={},
                content_type="multipart/form-data",
            ).status_code
            == 403
        )


def test_login_public(client):
    assert client.get("/login").status_code == 200
    resp = client.post(
        "/login", data={"username": "bad", "password": "bad"}, follow_redirects=False
    )
    assert resp.status_code in (200, 302)
    assert resp.status_code != 403
