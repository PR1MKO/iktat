from app import db
from app.models import Case
from tests.helpers import create_user, login_follow


def make_case(case_number: str, **kwargs) -> Case:
    case = Case(case_number=case_number, **kwargs)
    db.session.add(case)
    db.session.commit()
    return case


def test_leiro_ugyeim_lists_cases_for_default_leiro(client):
    leiro = create_user("leiro1", "pw", role="leíró", screen_name="Leiro One")
    login_follow(client, "leiro1", "pw")

    create_user(
        "szak1",
        "pw",
        role="szakértő",
        screen_name="Szak One",
        default_leiro_id=leiro.id,
    )

    make_case(
        "A-001",
        describer="Leiro One",
        expert_1="Szak One",
        status="boncolva-leírónál",
    )
    make_case(
        "B-002",
        describer="",
        expert_1="Szak One",
        status="boncolva-leírónál",
    )
    make_case(
        "C-003",
        describer=None,
        expert_1="szak1",
        status="leiktatva",
    )
    make_case(
        "E-005",
        describer=None,
        expert_2="Szak One",
        status="boncolva-leírónál",
    )

    other_leiro = create_user("leiroX", "pw", role="leíró", screen_name="Leiro X")
    create_user(
        "szakX",
        "pw",
        role="szakértő",
        screen_name="Szak X",
        default_leiro_id=other_leiro.id,
    )
    make_case(
        "D-004",
        describer=None,
        expert_1="Szak X",
        status="boncolva-leírónál",
    )

    response = client.get("/leiro/ugyeim")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "A-001" in body
    assert "B-002" in body
    assert "C-003" in body
    assert "E-005" in body
    assert "D-004" not in body


def test_leiro_ugyeim_respects_explicit_describer(client):
    leiro = create_user("leiro1", "pw", role="leíró", screen_name="Leiro One")
    create_user(
        "szak1",
        "pw",
        role="szakértő",
        screen_name="Szak One",
        default_leiro_id=leiro.id,
    )

    make_case(
        "F-006",
        describer="Another Person",
        expert_1="Szak One",
        status="boncolva-leírónál",
    )

    login_follow(client, "leiro1", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "F-006" not in body
