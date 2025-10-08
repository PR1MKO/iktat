"""Regression coverage for the Jegyzetek (notes) widget."""

from bs4 import BeautifulSoup
from flask import url_for

from app.models import Case, db
from tests.helpers import create_user, login


def _create_case_with_note(app, note_text="Első megjegyzés"):
    with app.app_context():
        case = Case(case_number="NT-100", status="beérkezett")
        case.notes = note_text
        db.session.add(case)
        db.session.commit()
        return case.id


def _create_notes_user(app, username="jegyzet_user"):
    with app.app_context():
        create_user(username, "pw", "iroda", screen_name="Jegyzet Elek")
    return username


def test_notes_initial_render_has_list_and_form(client, app):
    case_id = _create_case_with_note(app)
    username = _create_notes_user(app, "jegyzet_user_initial")
    login(client, username, "pw")

    with app.test_request_context():
        url = url_for("auth.case_detail", case_id=case_id)

    resp = client.get(url)
    assert resp.status_code == 200

    soup = BeautifulSoup(resp.data, "html.parser")
    notes_list = soup.select_one("#notes-list")
    assert notes_list is not None
    items = notes_list.select("li.list-group-item")
    assert items, "Existing notes should render as list-group items"
    assert soup.select_one("#new_note") is not None
    assert soup.select_one("#add-note-btn") is not None


def test_add_note_returns_persistent_snippet(client, app):
    case_id = _create_case_with_note(app)
    username = _create_notes_user(app, "jegyzet_user_post")
    login(client, username, "pw")

    with app.test_request_context():
        url = url_for("auth.add_note_universal", case_id=case_id)

    resp = client.post(url, json={"new_note": "Friss jegyzet"})
    assert resp.status_code == 200

    payload = resp.get_json()
    assert payload and "html" in payload
    html = payload["html"]
    assert '<div class="alert' in html or '<li class="list-group-item' in html


def test_page_still_has_form_after_add_note(client, app):
    case_id = _create_case_with_note(app)
    username = _create_notes_user(app, "jegyzet_user_flow")
    login(client, username, "pw")

    with app.test_request_context():
        page_url = url_for("auth.case_detail", case_id=case_id)
        post_url = url_for("auth.add_note_universal", case_id=case_id)

    initial_resp = client.get(page_url)
    assert initial_resp.status_code == 200
    initial_soup = BeautifulSoup(initial_resp.data, "html.parser")
    initial_items = initial_soup.select("#notes-list li")
    initial_count = len(initial_items)

    post_resp = client.post(post_url, json={"new_note": "Második jegyzet"})
    assert post_resp.status_code == 200

    refreshed_resp = client.get(page_url)
    assert refreshed_resp.status_code == 200
    refreshed_soup = BeautifulSoup(refreshed_resp.data, "html.parser")

    refreshed_items = refreshed_soup.select("#notes-list li")
    assert len(refreshed_items) == initial_count + 1
    assert refreshed_soup.select_one("#new_note") is not None
    assert refreshed_soup.select_one("#add-note-btn") is not None
