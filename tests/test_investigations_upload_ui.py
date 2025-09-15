import io

from tests.helpers import create_investigation, create_user, login


def test_investigations_detail_upload_form_placeholder_and_disabled(client, app):
    with app.app_context():
        create_user("admin", "secret", "admin")
        inv = create_investigation()
    login(client, "admin", "secret")
    resp = client.get(f"/investigations/{inv.id}")
    html = resp.get_data(as_text=True)
    assert "-- Válasszon kategóriát --" in html
    assert 'class="btn btn-outline-success upload-btn" disabled' in html


def test_investigations_upload_missing_category_rejected(client, app):
    with app.app_context():
        create_user("admin", "secret", "admin")
        inv = create_investigation()
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
