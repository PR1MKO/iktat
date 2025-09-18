import io

import pytest

from tests.helpers import create_investigation, create_user, login


@pytest.fixture
def make_investigation(app):
    def _make(**kwargs):
        with app.app_context():
            return create_investigation(**kwargs)

    return _make


@pytest.fixture
def login_as_szig_not_assigned(app, client):
    def _login():
        with app.app_context():
            create_user("sziggy", "secret", "szignáló")
        login(client, "sziggy", "secret")

    return _login


def test_admin_sees_upload_form_controls(client, app, make_investigation):
    with app.app_context():
        create_user("admin", "secret", "admin")
    inv = make_investigation()
    login(client, "admin", "secret")
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "-- Válasszon kategóriát --" in html
    assert "file-upload-form" in html
    assert "Csak a kijelölt" not in html


def test_investigations_upload_missing_category_rejected(
    client, app, make_investigation
):
    with app.app_context():
        create_user("admin", "secret", "admin")
    inv = make_investigation()
    login(client, "admin", "secret")
    data = {
        "category": "",
        "file": (io.BytesIO(b"%PDF-1.4"), "x.pdf"),
    }
    resp = client.post(
        f"/investigations/{inv.id}/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    text = resp.get_data(as_text=True)
    assert "Kategória megadása kötelező" in text


def test_non_member_sees_no_enabled_upload_controls(
    client, app, make_investigation, login_as_szig_not_assigned
):
    inv = make_investigation()
    login_as_szig_not_assigned()
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "alert-info" in html
    assert (
        "Nincs jogosultság fájl feltöltésére." in html
        or "Csak a kijelölt szakértők" in html
    )
    assert "file-upload-form" not in html


def test_forbidden_upload_renders_styled_page(
    client, app, make_investigation, login_as_szig_not_assigned
):
    inv = make_investigation()
    login_as_szig_not_assigned()
    resp = client.post(
        f"/investigations/{inv.id}/upload", data={}, follow_redirects=False
    )
    assert resp.status_code == 403
    html = resp.get_data(as_text=True)
    assert "Hozzáférés megtagadva" in html
    assert "Nincs jogosultság a kért művelethez." in html
