import pytest

from app import db
from app.models import Case
from tests.helpers import create_user, login


@pytest.fixture
def case_setup(app):
    with app.app_context():
        leiro = create_user(
            "leiro_default",
            "pw",
            "leíró",
            screen_name="Leíró One",
        )
        szak = create_user(
            "szak_default",
            "pw",
            "szakértő",
            screen_name="Szak One",
            default_leiro_id=leiro.id,
        )
        case = Case(
            case_number="T-016",
            status="boncolva-leírónál",
            expert_1=szak.screen_name,
            expert_2=None,
            describer=None,
        )
        db.session.add(case)
        db.session.commit()
        return {
            "case_id": case.id,
            "leiro_username": leiro.username,
            "fallback_label": leiro.screen_name,
        }


def test_case_detail_renders_default_leiro_when_missing(client, app, case_setup):
    with app.app_context():
        create_user("admin", "pw", "admin")
    login(client, "admin", "pw")

    resp = client.get(f"/cases/{case_setup['case_id']}/view")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert case_setup["fallback_label"] in body

    with app.app_context():
        refreshed = db.session.get(Case, case_setup["case_id"])
        assert not (refreshed.describer or "").strip()


def test_leiro_action_visible_with_fallback(client, case_setup):
    login(client, case_setup["leiro_username"], "pw")

    resp = client.get(f"/cases/{case_setup['case_id']}/view")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Elvégzem" in body


def test_fallback_does_not_persist_describer(client, app, case_setup):
    login(client, case_setup["leiro_username"], "pw")
    client.get(f"/cases/{case_setup['case_id']}/view")

    with app.app_context():
        refreshed = db.session.get(Case, case_setup["case_id"])
        assert refreshed.describer in (None, "")
