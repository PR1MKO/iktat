from datetime import date

from app import db
from app.investigations.models import Investigation
from tests.helpers import create_investigation, create_user, login


def _create_investigation(app):
    with app.app_context():
        inv = create_investigation(
            subject_name="Subject",
            investigation_type="type1",
            external_case_number="EXT-1",
            other_identifier="OID-1",
        )
        return inv.id


def test_edit_investigation_get_form(client, app):
    with app.app_context():
        create_user("iroda", "pw", "iroda")
    inv_id = _create_investigation(app)

    login(client, "iroda", "pw")
    resp = client.get(f"/investigations/{inv_id}/edit")

    assert resp.status_code == 200
    assert b"Vizsg\xc3\xa1lat szerkeszt\xc3\xa9se" in resp.data
    assert b'value="Subject"' in resp.data


def test_edit_investigation_post_updates(client, app):
    with app.app_context():
        create_user("iroda", "pw", "iroda")
        inv = create_investigation(
            subject_name="Old Name",
            mother_name="Mother",
            birth_place="Place",
            birth_date=date(2000, 1, 1),
            taj_number="123456789",
            residence="Address",
            citizenship="HU",
            institution_name="Inst",
            investigation_type="type1",
            external_case_number="EXT-1",
            other_identifier="OID-1",
        )
        inv_id = inv.id

    login(client, "iroda", "pw")

    resp = client.post(
        f"/investigations/{inv_id}/edit",
        data={
            "assignment_type": "INTEZETI",
            "assigned_expert_id": "0",
            "subject_name": "New Name",
            "maiden_name": "",
            "mother_name": "Mother",
            "birth_place": "Place",
            "birth_date": "2000-01-01",
            "taj_number": "123456789",
            "residence": "Address",
            "citizenship": "HU",
            "institution_name": "Inst",
            "investigation_type": "type1",
            "external_case_number": "EXT-1",
            "other_identifier": "",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/investigations/{inv_id}")

    with app.app_context():
        refreshed = db.session.get(Investigation, inv_id)
        assert refreshed.subject_name == "New Name"


def test_edit_investigation_requires_role(client, app):
    with app.app_context():
        create_user("expert", "pw", "szakértő")
    inv_id = _create_investigation(app)

    login(client, "expert", "pw")
    resp = client.get(f"/investigations/{inv_id}/edit")

    assert resp.status_code == 403
