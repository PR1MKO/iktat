import pytest

from app import db
from tests.helpers import create_investigation, create_user, login


def test_investigations_empty_states_render(app, client):
    create_user("sig_a", "pw", role="szignáló")
    login(client, "sig_a", "pw")
    resp = client.get("/szignal_cases")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Vizsgálatok" in html
    assert "Szakértők szerkesztése" in html
    assert "Nincs találat." in html


def test_investigations_lists_unassigned_and_with_expert(app, client):
    create_user("sig_b", "pw", role="szignáló")
    login(client, "sig_b", "pw")
    inv1 = create_investigation()
    inv2 = create_investigation(expert1_id=999)
    db.session.commit()
    resp = client.get("/szignal_cases")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    parts = html.split('id="investigations-unassigned"')[1].split(
        'id="investigations-with-expert"'
    )
    unassigned_html = parts[0]
    with_html = parts[1]
    assert str(inv1.id) in unassigned_html
    assert str(inv2.id) in with_html
