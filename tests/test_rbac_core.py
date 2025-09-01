import pytest

from app.models import Case, db
from tests.helpers import create_user, login


@pytest.mark.rbac
def test_rbac_enforcement(client, app):
    with app.app_context():
        create_user()
        create_user("office", "pw", "iroda")
        create_user("expert", "pw", "szakértő")
        case = Case(case_number="R1", expert_1="expert")
        db.session.add(case)
        db.session.commit()
        cid = case.id

    # Unauthenticated should redirect
    assert client.get("/cases").status_code == 302

    with client:
        login(client, "office", "pw")
        resp = client.post(f"/cases/{cid}/complete_expert")
        assert resp.status_code == 403

    with client:
        login(client, "expert", "pw")
        resp = client.post(f"/cases/{cid}/complete_expert")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/ugyeim")
    with app.app_context():
        assert db.session.get(Case, cid).status == "boncolva-leírónál"
