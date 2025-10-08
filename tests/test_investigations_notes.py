import pytest

from app.investigations.models import InvestigationNote
from tests.helpers import (
    create_investigation,
    create_investigation_with_default_leiro,
    create_user,
    login,
)


def test_default_leiro_can_post_note(app, client):
    with app.app_context():
        inv, leiro, _ = create_investigation_with_default_leiro()
        inv_id = inv.id
        username = leiro.username

    login(client, username, "secret")
    resp = client.post(
        f"/investigations/{inv_id}/notes",
        json={"text": "Megjegyzés a leíró által"},
    )
    assert resp.status_code in (200, 302)

    with app.app_context():
        assert (
            InvestigationNote.query.filter_by(
                investigation_id=inv_id, text="Megjegyzés a leíró által"
            ).first()
            is not None
        )


@pytest.mark.parametrize("alias", ["leíró", "leir", "LEIRO", "lei"])
def test_leiro_legacy_aliases_allowed_for_notes(app, client, alias):
    with app.app_context():
        inv, leiro, _ = create_investigation_with_default_leiro(role=alias)
        inv_id = inv.id
        username = leiro.username

    login(client, username, "secret")
    resp = client.post(
        f"/investigations/{inv_id}/notes",
        json={"text": f"alias ok {alias}"},
    )
    assert resp.status_code in (200, 302)


def test_investigation_notes_composer_hidden_for_unassigned_roles(app, client):
    with app.app_context():
        inv = create_investigation()
        user = create_user("unassigned_szak", "secret", "szakértő")
        inv_id = inv.id
        username = user.username

    login(client, username, "secret")
    resp = client.get(f"/investigations/{inv_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="notes-list"' in html
    assert 'id="add-note-btn"' not in html


def test_investigation_notes_composer_shown_for_assigned_member(app, client):
    with app.app_context():
        inv, leiro, _ = create_investigation_with_default_leiro()
        inv_id = inv.id
        username = leiro.username

    login(client, username, "secret")
    resp = client.get(f"/investigations/{inv_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="add-note-btn"' in html


def test_investigation_notes_post_for_unassigned_returns_403(app, client):
    with app.app_context():
        inv = create_investigation()
        user = create_user("unassigned_szak_post", "secret", "szakértő")
        inv_id = inv.id
        username = user.username

    login(client, username, "secret")
    resp = client.post(
        f"/investigations/{inv_id}/notes",
        json={"text": "unassigned attempt"},
    )
    assert resp.status_code == 403


def test_investigation_view_hides_composer_for_penzugy(app, client):
    with app.app_context():
        inv = create_investigation()
        user = create_user("penzugy_user", "secret", "pénzügy")
        inv_id = inv.id
        username = user.username

    login(client, username, "secret")
    resp = client.get(f"/investigations/{inv_id}/view")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="notes-list"' in html
    assert 'id="add-note-btn"' not in html


def test_investigation_notes_post_assigned_returns_200_fragment(app, client):
    with app.app_context():
        inv, leiro, _ = create_investigation_with_default_leiro()
        inv_id = inv.id
        username = leiro.username

    login(client, username, "secret")
    resp = client.post(
        f"/investigations/{inv_id}/notes",
        json={"text": "assigned ok"},
    )
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    if resp.is_json:
        payload = resp.get_json()
        assert payload and payload.get("html")
    else:
        assert "assigned ok" in body
