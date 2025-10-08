from bs4 import BeautifulSoup
from flask import url_for

from app.models import Case, db
from tests.helpers import create_investigation, create_user, login


def _create_case(app, note_text="Első megjegyzés"):
    with app.app_context():
        case = Case(case_number="CSP-001", status="beérkezett")
        case.notes = note_text
        db.session.add(case)
        db.session.commit()
        return case.id


def _login_case_user(app, client, username="csp_notes_user"):
    with app.app_context():
        create_user(username, "pw", "iroda", screen_name="CSP Notes")
    login(client, username, "pw")


def _assert_scripts_have_nonce(soup):
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            assert script.get("nonce"), f"external script {src} missing nonce"
        else:
            assert (
                script.get("type") == "application/json"
            ), "inline scripts must be data blocks"


def test_case_detail_notes_markup_csp(client, app):
    case_id = _create_case(app)
    _login_case_user(app, client)

    with app.test_request_context():
        page_url = url_for("auth.case_detail", case_id=case_id)
        post_url = url_for("auth.add_note_universal", case_id=case_id)

    resp = client.get(page_url)
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.data, "html.parser")
    _assert_scripts_have_nonce(soup)

    form = soup.select_one("#notes-form")
    assert form is not None
    assert form.get("data-case-id") == str(case_id)

    notes_list = form.select_one("#notes-list")
    assert notes_list is not None

    button = form.select_one("#add-note-btn")
    assert button is not None
    assert button.get("data-notes-url") == post_url

    post_resp = client.post(post_url, json={"new_note": "Új CSP jegyzet"})
    assert post_resp.status_code == 200
    payload = post_resp.get_json()
    assert payload and "Új CSP jegyzet" in payload.get("html", "")


def test_investigation_view_notes_markup_csp(client, app):
    with app.app_context():
        inv = create_investigation()
        user = create_user("iroda_csp", "pw", "iroda")
        inv_id = inv.id
        username = user.username

    login(client, username, "pw")

    with app.test_request_context():
        post_url = url_for("investigations.add_investigation_note", id=inv_id)

    resp = client.get(f"/investigations/{inv_id}/view")
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.data, "html.parser")
    _assert_scripts_have_nonce(soup)

    notes_list = soup.select_one("#notes-list")
    assert notes_list is not None

    button = soup.select_one("#add-note-btn")
    assert button is not None
    assert button.get("data-notes-url") == post_url

    post_resp = client.post(post_url, json={"text": "Vizsgálati CSP jegyzet"})
    assert post_resp.status_code == 200
    body = post_resp.get_data(as_text=True)
    assert "Vizsgálati CSP jegyzet" in body
