from app.models import Case, TaskMessage, db
from app.utils.time_utils import now_local
from tests.helpers import create_user, login


def _create_case(case_number="C100", **kw):
    case = Case(case_number=case_number, registration_time=now_local(), **kw)
    db.session.add(case)
    db.session.commit()
    return case


def test_idempotency_certificate_double_post_ignored(
    client, app, tmp_path, monkeypatch
):
    with app.app_context():
        create_user("doc", "pw", "szakértő")
        case = _create_case(expert_1="doc")
        cid = case.id
        monkeypatch.setattr("app.paths.ensure_case_folder", lambda x: tmp_path)
    form = {
        "halalt_megallap": "x",
        "boncolas_tortent": "igen",
        "varhato_tovabbi_vizsgalat": "nem",
        "kozvetlen_halalok": "ok",
        "kozvetlen_halalok_ido": "1",
        "alapbetegseg_szovodmenyei": "a",
        "alapbetegseg_szovodmenyei_ido": "2",
        "alapbetegseg": "b",
        "alapbetegseg_ido": "3",
        "kiserobetegsegek": "c",
    }
    login(client, "doc", "pw")
    resp1 = client.post(
        f"/ugyeim/{cid}/generate_certificate", data=form, follow_redirects=True
    )
    assert resp1.status_code == 200
    with app.app_context():
        first = db.session.get(Case, cid).certificate_generated_at
    resp2 = client.post(
        f"/ugyeim/{cid}/generate_certificate", data=form, follow_redirects=True
    )
    assert "Művelet már feldolgozva." in resp2.get_data(as_text=True)
    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.certificate_generated_at == first


def test_assign_pathologist_idempotent_same_assignment(client, app, monkeypatch):
    with app.app_context():
        create_user("szig", "pw", "szignáló")
        create_user("exp", "pw", "szakértő")
        case = _create_case()
        version = case.updated_at.isoformat()
        cid = case.id
    monkeypatch.setattr("app.views.auth.send_email", lambda *a, **k: None)
    login(client, "szig", "pw")
    form = {
        "action": "assign",
        "expert_1": "exp",
        "expert_2": "",
        "form_version": version,
    }
    resp1 = client.post(
        f"/szignal_cases/{cid}/assign", data=form, follow_redirects=True
    )
    assert resp1.status_code == 200
    with app.app_context():
        version2 = db.session.get(Case, cid).updated_at.isoformat()
    form2 = {
        "action": "assign",
        "expert_1": "exp",
        "expert_2": "",
        "form_version": version2,
    }
    resp2 = client.post(
        f"/szignal_cases/{cid}/assign", data=form2, follow_redirects=False
    )
    assert resp2.status_code == 302
    with app.app_context():
        msgs = TaskMessage.query.filter_by(case_id=cid).all()
        assert len(msgs) == 1


def test_assign_describer_idempotent_json(client, app):
    with app.app_context():
        create_user("szak", "pw", "szakértő")
        case = _create_case(expert_1="szak", started_by_expert=True)
        cid = case.id
    login(client, "szak", "pw")
    resp1 = client.post(f"/ugyeim/{cid}/assign_describer", json={"describer": "d"})
    assert resp1.status_code == 204
    resp2 = client.post(f"/ugyeim/{cid}/assign_describer", json={"describer": "d"})
    assert resp2.status_code == 409
    assert resp2.get_json()["error"] == "Művelet már feldolgozva"


def test_edit_case_stale_form_rejected(client, app):
    with app.app_context():
        create_user("admin", "pw", "admin")
        case = _create_case(deceased_name="orig")
        cid = case.id
        token = case.updated_at.isoformat()
    login(client, "admin", "pw")
    client.get(f"/cases/{cid}/edit")
    with app.app_context():
        c = db.session.get(Case, cid)
        c.deceased_name = "changed"
        db.session.commit()
    resp = client.post(
        f"/cases/{cid}/edit",
        data={"deceased_name": "new", "form_version": token},
        follow_redirects=True,
    )
    assert "Az űrlap időközben frissült." in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Case, cid).deceased_name == "changed"


def test_edit_case_basic_stale_form_rejected(client, app):
    with app.app_context():
        create_user("iroda", "pw", "iroda")
        case = _create_case(deceased_name="orig")
        cid = case.id
        token = case.updated_at.isoformat()
    login(client, "iroda", "pw")
    client.get(f"/cases/{cid}/edit_basic")
    with app.app_context():
        c = db.session.get(Case, cid)
        c.deceased_name = "changed"
        db.session.commit()
    resp = client.post(
        f"/cases/{cid}/edit_basic",
        data={"deceased_name": "new", "form_version": token},
        follow_redirects=True,
    )
    assert "Az űrlap időközben frissült." in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Case, cid).deceased_name == "changed"
