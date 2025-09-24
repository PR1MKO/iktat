import pytest

from app.investigations.models import InvestigationNote
from tests.helpers import create_investigation_with_default_leiro, login


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
