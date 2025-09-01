import io

from app.models import Case, UploadedFile, User, db
from tests.helpers import create_user, login


def test_protected_routes_require_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp = client.get("/cases/new")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_access_admin_routes(client, app):
    with app.app_context():
        create_user("admin1", "pw", "admin")
        case = Case(case_number="A1")
        db.session.add(case)
        db.session.commit()
    with client:
        login(client, "admin1", "pw")
        assert client.get("/admin/users").status_code == 200
        assert client.get("/admin/cases").status_code == 200
        # assignment routes restricted to szignáló in code
        resp = client.get("/szignal_cases")
        assert resp.status_code == 403


def test_iroda_permissions(client, app):
    with app.app_context():
        create_user("office", "pw", "iroda")
        case = Case(case_number="I1")
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, "office", "pw")
        assert client.get("/cases/new").status_code == 200
        data = {"file": (io.BytesIO(b"x"), "test.pdf"), "category": "egyéb"}
        resp = client.post(
            f"/cases/{cid}/upload", data=data, content_type="multipart/form-data"
        )
        assert resp.status_code == 302
        # forbidden actions
        assert client.get("/admin/users").status_code == 403
        assert client.post(f"/admin/cases/{cid}/delete").status_code == 403
        assert client.get("/szignal_cases").status_code == 403


def test_szakerto_permissions(client, app):
    with app.app_context():
        create_user("doc", "pw", "szakértő")
        case = Case(case_number="S1", expert_1="doc")
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, "doc", "pw")
        # access own case execution view
        assert client.get(f"/ugyeim/{cid}/elvegzem").status_code == 200
        # cannot access admin or assignment routes
        assert client.get("/admin/users").status_code == 403
        assert client.get("/szignal_cases").status_code == 403


def test_toxi_permissions_and_dashboard_redirect(client, app):
    with app.app_context():
        create_user("tox", "pw", "toxi")
        case = Case(case_number="T1", tox_expert="tox")
        db.session.add(case)
        db.session.commit()
    with client:
        login(client, "tox", "pw")
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert "/ugyeim/toxi" in resp.headers["Location"]
        resp = client.get("/ugyeim/toxi")
        assert resp.status_code == 200
        assert b"Toxikologi" in resp.data or b"Toxikol" in resp.data


def test_toxi_dashboard_lists_cases(client, app):
    with app.app_context():
        tox_user = User(username="tox", screen_name="Toxi", role="toxi")
        tox_user.set_password("pw")
        db.session.add(tox_user)

        c1 = Case(case_number="C1")
        c2 = Case(case_number="C2", tox_completed=True)
        c3 = Case(case_number="C3", tox_completed=None)
        c4 = Case(case_number="C4")
        db.session.add_all([c1, c2, c3, c4])
        db.session.commit()

        for case in (c1, c2, c3):
            db.session.add(
                UploadedFile(
                    case_id=case.id,
                    filename="file.txt",
                    uploader="tox",
                    category="végzés",
                )
            )
        db.session.commit()

    with client:
        login(client, "tox", "pw")
        resp = client.get("/ugyeim/toxi")
        text = resp.data.decode("utf-8")
        assert "C1" in text
        assert "C2" in text
        assert "C3" in text
        assert "C4" not in text
