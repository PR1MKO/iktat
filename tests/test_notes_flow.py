"""Regression tests for AJAX note submission widgets."""

import pytest
from flask import url_for

from app.models import Case, db
from tests.helpers import create_user, login


@pytest.fixture
def case_id(app):
    with app.app_context():
        case = Case(case_number="T-900", status="beérkezett")
        db.session.add(case)
        db.session.commit()
        return case.id


def test_add_note_universal_json(client, app, case_id):
    with app.app_context():
        create_user("iroda_user", "pw", "iroda", screen_name="Iroda User")
    login(client, "iroda_user", "pw")

    with app.test_request_context():
        url = url_for("auth.add_note_universal", case_id=case_id)

    resp = client.post(url, json={"new_note": "hello world"})

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload and "html" in payload and "hello world" in payload["html"]

    with app.app_context():
        refreshed = db.session.get(Case, case_id)
        assert "hello world" in (refreshed.notes or "")


def test_notes_template_renders_controls_and_global_script(client, app, case_id):
    with app.app_context():
        create_user("toxi_user", "pw", "toxi", screen_name="Toxi User")
    login(client, "toxi_user", "pw")

    with app.test_request_context():
        url = url_for("main.elvegzem_toxi", case_id=case_id)

    resp = client.get(url)
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert 'id="notes-form"' in html
    assert '<input type="hidden" name="csrf_token"' in html
    assert "/static/js/notes.js" in html
