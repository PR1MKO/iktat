import re

import pytest

from app.models import Case, db
from app.utils.time_utils import now_local
from tests.helpers import create_investigation, create_user, login


def setup_login_fail(app, client, monkeypatch):
    return "/login", {"username": "x", "password": "y"}, "Invalid username or password."


def setup_case_new_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    return (
        "/cases/new",
        {"case_type": "", "beerk_modja": "", "institution_name": ""},
        "Típus, Beérkezés módja, Intézmény neve kitöltése kötelező.",
    )


def setup_case_edit_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    case = Case(case_number="E1", registration_time=now_local(), status="beérkezett")
    db.session.add(case)
    db.session.commit()

    def boom():
        raise Exception("fail")

    monkeypatch.setattr(db.session, "commit", boom)
    return (
        f"/cases/{case.id}/edit",
        {"deceased_name": ""},
        "Valami hiba történt. Próbáld újra.",
    )


def setup_case_edit_basic_fail(app, client, monkeypatch):
    create_user("iroda", "pw", "iroda")
    login(client, "iroda", "pw")
    case = Case(case_number="B1", registration_time=now_local(), status="beérkezett")
    db.session.add(case)
    db.session.commit()

    def boom():
        raise Exception("fail")

    monkeypatch.setattr(db.session, "commit", boom)
    return (
        f"/cases/{case.id}/edit_basic",
        {"deceased_name": ""},
        "Valami hiba történt. Próbáld újra.",
    )


def setup_case_documents_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    case = Case(case_number="C1", registration_time=now_local(), status="beérkezett")
    db.session.add(case)
    db.session.commit()

    def boom():
        raise Exception("fail")

    monkeypatch.setattr(db.session, "commit", boom)
    return (
        f"/cases/{case.id}/documents",
        {"tox_ordered": "1"},
        "Valami hiba történt. Próbáld újra.",
    )


def setup_add_user_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    return (
        "/admin/users/add",
        {"username": "x", "password": "y", "role": ""},
        "This field is required.",
    )


def setup_edit_user_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    target = create_user("target", "pw", "iroda")
    login(client, "admin", "secret")

    def boom():
        raise Exception("fail")

    monkeypatch.setattr(db.session, "commit", boom)
    return (
        f"/admin/users/{target.id}/edit",
        {"username": "target", "role": "iroda"},
        "Valami hiba történt. Próbáld újra.",
    )


def setup_new_investigation_fail(app, client, monkeypatch):
    create_user("admin", "secret", "admin")
    login(client, "admin", "secret")
    return "/investigations/new", {"subject_name": ""}, "This field is required."


SETUPS = [
    setup_login_fail,
    setup_case_new_fail,
    setup_case_edit_fail,
    setup_case_edit_basic_fail,
    setup_case_documents_fail,
    setup_add_user_fail,
    setup_edit_user_fail,
    setup_new_investigation_fail,
]


@pytest.mark.parametrize("setup", SETUPS)
def test_prg_redirects(client, app, monkeypatch, setup):
    url, data, message = setup(app, client, monkeypatch)
    resp = client.post(url, data=data, follow_redirects=True)
    assert any(r.status_code == 302 for r in resp.history)
    assert message in resp.get_data(as_text=True)


@pytest.mark.parametrize("setup", SETUPS)
def test_prg_disabled_renders(client, app, monkeypatch, setup):
    app.config["STRICT_PRG_ENABLED"] = False
    url, data, message = setup(app, client, monkeypatch)
    resp = client.post(url, data=data, follow_redirects=False)
    assert resp.status_code == 200
    assert message in resp.get_data(as_text=True)


def test_csp_nonce_present_and_non_empty_on_documents(client, app):
    with app.app_context():
        user = create_user()
        inv = create_investigation()
        username = user.username
        inv_id = inv.id
    login(client, username, "secret")
    resp = client.get(f"/investigations/{inv_id}/documents")
    html = resp.get_data(as_text=True)
    # Nonce must be present and start with an alphanumeric character
    assert 'nonce="' in html
    m = re.search(r'nonce="([A-Za-z0-9][A-Za-z0-9_-]{10,})"', html)
    assert m, "CSP nonce must be present and start with an alphanumeric character."
