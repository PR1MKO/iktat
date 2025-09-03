from datetime import date

from tests.helpers import create_user, login


def _payload():
    return {
        "assignment_type": "INTEZETI",
        "investigation_type": "DEFAULT",
        "subject_name": "Teszt Alany",
        "mother_name": "Teszt Anya",
        "external_case_number": "",
        "other_identifier": "",
        "birth_date": date.today().isoformat(),
        "birth_place": "Budapest",
        "taj_number": "123456789",
        "residence": "Budapest, Minta u. 1.",
        "citizenship": "magyar",
    }


def test_post_new_investigation_creates_row(client, app):
    with app.app_context():
        create_user()
    login(client, "admin", "secret")
    resp = client.post("/investigations/new", data=_payload(), follow_redirects=False)
    assert resp.status_code in (302, 303)
