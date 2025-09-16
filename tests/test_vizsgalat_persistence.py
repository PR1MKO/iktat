from datetime import datetime, timezone

from app.models import Case, db
from app.utils.time_utils import fmt_budapest
from tests.helpers import create_user, login


def test_vizsgalat_orders_persist(client, app, monkeypatch):
    with app.app_context():
        create_user("doc", "pw", "szakértő")
        case = Case(case_number="P1", expert_1="doc")
        db.session.add(case)
        db.session.commit()
        cid = case.id

    t1 = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.routes.now_utc", lambda: t1)
    with client:
        login(client, "doc", "pw")
        data = {"alkohol_ver_ordered": "on", "alkohol_ver": "1"}
        resp = client.post(f"/ugyeim/{cid}/vizsgalat_elrendelese", data=data)
        assert resp.status_code == 302

    t2 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("app.routes.now_utc", lambda: t2)
    with client:
        login(client, "doc", "pw")
        data = {"tox_cpk_ordered": "on", "tox_cpk": "2"}
        resp = client.post(f"/ugyeim/{cid}/vizsgalat_elrendelese", data=data)
        assert resp.status_code == 302

    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.alkohol_ver_ordered is True
        assert case.alkohol_ver == "1"
        assert case.tox_cpk_ordered is True
        assert case.tox_cpk == "2"
        lines = case.tox_orders.strip().splitlines()
        assert len(lines) == 2
        assert lines[0] == f"Alkohol vér rendelve (1): {fmt_budapest(t1)} – doc"
        assert lines[1] == f"CPK rendelve (2): {fmt_budapest(t2)} – doc"
