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


def test_leiro_ugyeim_explicit_match_normalizes_identifiers(client):
    leiro = create_user(
        "LeIrO1",
        "pw",
        role="leíró",
        screen_name="",
    )
    login_follow(client, "LeIrO1", "pw")

    make_case(
        "WS-101",
        describer="  leiro1  ",
        status="boncolva-leírónál",
    )

    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "WS-101" in body


def test_leiro_ugyeim_default_mapping_handles_whitespace_and_case(client):
    leiro = create_user("le1", "pw", role="leíró", screen_name="Leíró One")
    create_user(
        "SZAK1",
        "pw",
        role="szakértő",
        screen_name="  Szak One  ",
        default_leiro_id=leiro.id,
    )

    login_follow(client, "le1", "pw")

    make_case(
        "WS-202",
        expert_1="  szak one  ",
        status="boncolva-leírónál",
    )

    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "WS-202" in body


def test_leiro_ugyeim_excludes_cases_for_other_default_leiro(client):
    me = create_user("me", "pw", role="leíró", screen_name="Me")
    other = create_user("other", "pw", role="leíró", screen_name="Other")
    create_user(
        "szakx",
        "pw",
        role="szakértő",
        screen_name="Szak X",
        default_leiro_id=other.id,
    )

    login_follow(client, "me", "pw")

    make_case(
        "NEG-303",
        expert_1="Szak X",
        status="boncolva-leírónál",
    )

    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "NEG-303" not in body
