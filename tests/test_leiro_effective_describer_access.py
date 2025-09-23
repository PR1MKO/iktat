from app import db
from app.models import Case
from tests.helpers import create_user, login_follow


def test_leiro_elvegzem_allows_default_leiro_when_describer_empty(client, app):
    with app.app_context():
        leiro = create_user("leiro1", "pw", role="leíró", screen_name="Leiro One")
        _ = create_user(
            "szak1",
            "pw",
            role="szakértő",
            screen_name="Szak One",
            default_leiro_id=leiro.id,
        )
        case = Case(
            case_number="A-LEI-001",
            status="boncolva-leírónál",
            expert_1="Szak One",
            describer="",
        )
        db.session.add(case)
        db.session.commit()
        cid = case.id

    login_follow(client, "leiro1", "pw")
    resp = client.get(f"/leiro/ugyeim/{cid}/elvegzem", follow_redirects=True)
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Nincs jogosultságod az ügy elvégzéséhez." not in body
    assert "Elvégezve" in body or "Ügy elvégzése" in body


def test_leiro_elvegzem_warns_when_not_at_leiro_stage_for_default_leiro(client, app):
    with app.app_context():
        leiro = create_user("leiro2", "pw", role="leíró", screen_name="Leiro Two")
        _ = create_user(
            "szak2",
            "pw",
            role="szakértő",
            screen_name="Szak Two",
            default_leiro_id=leiro.id,
        )
        case = Case(
            case_number="A-LEI-002",
            status="szignálva",
            expert_1="Szak Two",
            describer="",
        )
        db.session.add(case)
        db.session.commit()
        cid = case.id

    login_follow(client, "leiro2", "pw")
    resp = client.get(f"/leiro/ugyeim/{cid}/elvegzem", follow_redirects=True)
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "Az ügy nincs a leírónál." in body
