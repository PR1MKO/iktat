import re

from app.utils import permissions as permissions_mod
from tests.helpers import create_investigation, create_user, login


def _find_tag(pattern, html):
    match = re.search(pattern, html, re.S)
    assert match is not None
    return match.group(0)


def test_assign_page_requires_login(client, app):
    with app.app_context():
        inv = create_investigation()

    resp = client.get(f"/investigations/{inv.id}/assign")
    assert resp.status_code in (302, 401)
    if resp.status_code == 302:
        assert "/login" in resp.headers.get("Location", "")


def test_assign_page_allows_szignal_upload_controls(client, app):
    with app.app_context():
        inv = create_investigation()
        create_user("signer", "secret", "szignáló")

    login(client, "signer", "secret")
    resp = client.get(f"/investigations/{inv.id}/assign")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    file_tag = _find_tag(r'<input[^>]+id="investigation-file"[^>]*>', html)
    select_tag = _find_tag(
        r'<select[^>]+id="upload-category-file-upload-form"[^>]*>', html
    )
    button_tag = _find_tag(
        r'<button[^>]+class="btn btn-outline-success upload-btn"[^>]*>', html
    )

    assert "disabled" not in file_tag
    assert "disabled" not in select_tag
    assert 'type="submit"' in button_tag
    assert "alert alert-warning" not in html


def test_assign_page_disables_upload_without_capability(client, app, monkeypatch):
    with app.app_context():
        inv = create_investigation()
        create_user("signer", "secret", "szignáló")

    original = permissions_mod.capabilities_for

    def _no_upload(user):
        caps = original(user)
        caps["can_upload_investigation"] = False
        return caps

    monkeypatch.setattr(permissions_mod, "capabilities_for", _no_upload)

    login(client, "signer", "secret")
    resp = client.get(f"/investigations/{inv.id}/assign")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    file_tag = _find_tag(r'<input[^>]+id="investigation-file"[^>]*>', html)
    select_tag = _find_tag(
        r'<select[^>]+id="upload-category-file-upload-form"[^>]*>', html
    )

    assert "disabled" in file_tag
    assert "disabled" in select_tag
    assert "btn btn-outline-success upload-btn" not in html
    assert "Nincs jogosultság fájlfeltöltéshez ezen az oldalon." in html
