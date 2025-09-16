import io
import os
import shutil
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import inspect

from app import db
from app.investigations import utils as inv_utils
from app.investigations.models import Investigation, InvestigationNote
from app.models import Case
from tests.helpers import create_investigation, create_user, login


@pytest.fixture(autouse=True)
def _ensure_main_schema_autouse(app):
    """
    Ensure the default (main) bind has its schema before any tests in this module run.
    This prevents OperationalError: no such table: user when only the 'examination' bind
    was initialized by a preceding fixture.
    """
    with app.app_context():
        insp = inspect(db.engine)
        if "user" not in insp.get_table_names():
            db.create_all(bind_key=None)


def _base_form_data():
    return {
        "subject_name": "Teszt Alany",
        "mother_name": "Teszt Anya",
        "birth_place": "Budapest",
        "birth_date": "2000-01-02",
        "taj_number": "123456789",
        "residence": "Cím",
        "citizenship": "magyar",
        "institution_name": "Intézet",
        "investigation_type": "type1",
    }


def test_investigation_db_isolation(app):
    with app.app_context():
        assert Investigation.__bind_key__ == "examination"
        default_engine = db.engines[None]
        exam_engine = db.engines["examination"]
        assert default_engine.url.database != exam_engine.url.database
        create_investigation()
        assert Case.query.count() == 0


def test_case_number_sequential_and_year_reset(app, monkeypatch):
    with app.app_context():

        def fake_now(year):
            return datetime(year, 1, 1, tzinfo=timezone.utc)

        monkeypatch.setattr(inv_utils, "now_utc", lambda: fake_now(2023))
        cn1 = inv_utils.generate_case_number(db.session)
        create_investigation(case_number=cn1)
        cn2 = inv_utils.generate_case_number(db.session)
        assert cn2 == "V:0002/2023"
        create_investigation(case_number=cn2)
        monkeypatch.setattr(inv_utils, "now_utc", lambda: fake_now(2024))
        cn3 = inv_utils.generate_case_number(db.session)
        assert cn3 == "V:0001/2024"


from app.investigations.forms import InvestigationForm


def test_creation_requires_identifier(app):
    data = _base_form_data()
    data.update({"external_case_number": "", "other_identifier": ""})
    form = InvestigationForm(data=data)
    assert not form.validate()
    assert form.external_case_number.errors
    assert form.other_identifier.errors


def test_creation_requires_mandatory_fields(app):
    data = _base_form_data()
    data.update({"external_case_number": "EXT1"})
    data["subject_name"] = ""
    form = InvestigationForm(data=data)
    assert not form.validate()
    assert form.subject_name.errors


@pytest.fixture
def _search_data(app):
    with app.app_context():
        inv1 = create_investigation(
            case_number="V:0001/2023",
            external_case_number="EXT123",
            other_identifier="OID456",
            subject_name="John Doe",
            maiden_name="Smith",
            investigation_type="type1",
            mother_name="Jane",
            birth_place="Budapest",
            birth_date=date(1990, 1, 1),
            taj_number="TAJ111",
            residence="Budapest Address",
            citizenship="Hungarian",
            institution_name="Clinic",
        )
        create_investigation(
            case_number="V:0002/2023",
            external_case_number="DIFF",
            other_identifier="DIFF2",
            subject_name="Alice Roe",
            maiden_name="Roe",
            investigation_type="type2",
            mother_name="Mary",
            birth_place="Debrecen",
            birth_date=date(1991, 1, 1),
            taj_number="TAJ222",
            residence="Other",
            citizenship="Other",
            institution_name="Hospital",
        )
        return inv1


@pytest.mark.parametrize(
    "query",
    [
        "0001",
        "EXT",
        "OID",
        "John",
        "Smi",
        "type1",
        "Jane",
        "Buda",
        "1990",
        "TAJ111",
        "Address",
        "Hungar",
        "Clinic",
    ],
)
def test_search_filters_across_fields(client, app, _search_data, query):
    with app.app_context():
        create_user()
    login(client, "admin", "secret")
    resp = client.get(f"/investigations/?q={query}")
    assert b"V:0001/2023" in resp.data
    assert b"V:0002/2023" not in resp.data


def test_investigation_upload_ajax_json_contract(client, app):
    with app.app_context():
        user = create_user()
        inv = create_investigation()
        username = user.username
        inv_id = inv.id
        case_number = inv.case_number
    login(client, username, "secret")
    data = {
        "category": "option1",
        "file": (io.BytesIO(b"hello"), "file.pdf"),
    }
    resp = client.post(
        f"/investigations/{inv_id}/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    assert resp.is_json
    payload = resp.get_json()
    for key in ("id", "filename", "category", "uploaded_at"):
        assert key in payload
    from app.paths import ensure_investigation_folder

    inv_dir = ensure_investigation_folder(case_number)
    upload_path = os.path.join(inv_dir, "file.pdf")
    assert os.path.exists(upload_path)
    os.remove(upload_path)
    shutil.rmtree(inv_dir)


def test_investigation_upload_prg_redirects_when_not_ajax(client, app):
    with app.app_context():
        user = create_user()
        inv = create_investigation()
        username = user.username
        inv_id = inv.id
    login(client, username, "secret")
    resp = client.post(
        f"/investigations/{inv_id}/upload",
        data={"category": "option1", "file": (io.BytesIO(b"x"), "x.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    assert f"/investigations/{inv_id}/documents" in resp.headers["Location"]


def test_note_creation(client, app):
    with app.app_context():
        user = create_user()
        inv = create_investigation()
        username = user.username
        user_id = user.id
        inv_id = inv.id
    login(client, username, "secret")
    resp = client.post(f"/investigations/{inv_id}/notes", json={"text": "hello note"})
    assert resp.status_code == 200
    assert b"hello note" in resp.data
    assert username.encode() in resp.data
    with app.app_context():
        note = InvestigationNote.query.filter_by(investigation_id=inv_id).one()
        assert note.author_id == user_id
        assert note.timestamp is not None


def test_permissions(client, app):
    from flask_login import login_user
    from werkzeug.exceptions import Forbidden

    from app.investigations.routes import new_investigation

    with app.app_context():
        create_user()  # admin
        expert = create_user(username="expert", role="szakértő")
        other = create_user(username="other", role="szakértő")
        inv = create_investigation(expert1_id=expert.id)
        inv_id = inv.id
        case_number = inv.case_number
        data = _base_form_data()
        data.update({"external_case_number": "EXT1"})
        with app.test_request_context("/investigations/new", method="POST", data=data):
            login_user(expert)
            with pytest.raises(Forbidden):
                new_investigation()
    # non admin cannot edit
    login(client, "expert", "secret")
    resp = client.post(f"/investigations/{inv_id}/edit", data=data)
    assert resp.status_code == 403
    # assigned expert can add note and upload
    resp = client.post(f"/investigations/{inv_id}/notes", json={"text": "hi"})
    assert resp.status_code == 200
    resp = client.post(
        f"/investigations/{inv_id}/upload",
        data={"category": "option1", "file": (io.BytesIO(b"x"), "x.pdf")},
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    from app.paths import ensure_investigation_folder

    inv_dir = ensure_investigation_folder(case_number)
    upload_path = os.path.join(inv_dir, "x.pdf")
    assert os.path.exists(upload_path)
    os.remove(upload_path)
    shutil.rmtree(inv_dir)
    # unassigned user blocked
    login(client, "other", "secret")
    resp = client.post(f"/investigations/{inv_id}/notes", json={"text": "hi"})
    assert resp.status_code == 403
    resp = client.post(
        f"/investigations/{inv_id}/upload",
        data={"category": "option1", "file": (io.BytesIO(b"x"), "y.txt")},
        content_type="multipart/form-data",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 403


def test_new_page_shows_assignment_fields(client, app):
    with app.app_context():
        create_user()  # admin
        create_user(username="expert", role="szakértő")
    login(client, "admin", "secret")
    resp = client.get("/investigations/new")
    assert b'id="assignment_type-intezeti"' in resp.data
    assert b'id="assignment_type-szakertoi"' in resp.data
    assert b'id="assigned_expert_id"' in resp.data
    assert b'id="assigned_expert_id"' in resp.data and b"disabled" in resp.data


def test_post_intezeti_sets_no_expert(client, app):
    with app.app_context():
        create_user()  # admin
        expert = create_user(username="exp", role="szakértő")
        expert_id = expert.id
    login(client, "admin", "secret")
    data = _base_form_data()
    data.update(
        {
            "external_case_number": "EXT1",
            "assignment_type": "INTEZETI",
            "assigned_expert_id": expert_id,
        }
    )
    resp = client.post("/investigations/new", data=data, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        inv = Investigation.query.order_by(Investigation.id.desc()).first()
        assert inv.assignment_type == "INTEZETI"
        assert inv.assigned_expert_id is None


def test_post_szakertoi_requires_expert(client, app):
    with app.app_context():
        create_user()  # admin
        create_user(username="exp", role="szakértő")
    login(client, "admin", "secret")
    data = _base_form_data()
    data.update(
        {
            "external_case_number": "EXT1",
            "assignment_type": "SZAKÉRTŐI",
            "assigned_expert_id": 0,
        }
    )
    resp = client.post("/investigations/new", data=data, follow_redirects=True)
    assert any(r.status_code == 302 for r in resp.history)
    assert "Szakértő kiválasztása kötelező." in resp.get_data(as_text=True)
    with app.app_context():
        assert Investigation.query.count() == 0


def test_post_szakertoi_persists_expert(client, app):
    with app.app_context():
        create_user()  # admin
        expert = create_user(username="exp", role="szakértő")
        expert_id = expert.id
    login(client, "admin", "secret")
    data = _base_form_data()
    data.update(
        {
            "external_case_number": "EXT1",
            "assignment_type": "SZAKÉRTŐI",
            "assigned_expert_id": expert_id,
        }
    )
    resp = client.post("/investigations/new", data=data, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        inv = Investigation.query.order_by(Investigation.id.desc()).first()
        assert inv.assignment_type == "SZAKÉRTŐI"
        assert inv.assigned_expert_id == expert_id
