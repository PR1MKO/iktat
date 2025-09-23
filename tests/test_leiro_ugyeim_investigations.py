from tests.helpers import create_investigation, create_user, login_follow


def test_default_leiro_sees_unassigned_investigation(client):
    leiro = create_user("leiro-default", "pw", role="leíró", screen_name="Leíró")
    expert = create_user(
        "szak-default",
        "pw",
        role="szakértő",
        screen_name="Szakértő",
        default_leiro_id=leiro.id,
    )
    inv = create_investigation(
        subject_name="Minta Alany",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
    )

    login_follow(client, "leiro-default", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "Minta Alany" in body
    assert f'href="/investigations/{inv.id}/leiro/elvegzem"' in body
    assert "Elvégzem" in body


def test_explicit_describer_always_included(client):
    leiro = create_user("leiro-explicit", "pw", role="leíró", screen_name="Leíró")
    expert = create_user(
        "szak-explicit",
        "pw",
        role="szakértő",
        screen_name="Szakértő",
        default_leiro_id=None,
    )
    create_investigation(
        subject_name="Közvetlen Vizsgálat",
        status="beérkezett",
        expert1_id=expert.id,
        describer_id=leiro.id,
    )

    login_follow(client, "leiro-explicit", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "Közvetlen Vizsgálat" in body


def test_investigations_for_other_default_leiro_excluded(client):
    me = create_user("leiro-me", "pw", role="leíró", screen_name="Első")
    other = create_user("leiro-other", "pw", role="leíró", screen_name="Másik")
    expert = create_user(
        "szak-other",
        "pw",
        role="szakértő",
        screen_name="Szak Másik",
        default_leiro_id=other.id,
    )
    create_investigation(
        subject_name="Másikhoz Tartozó",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
    )

    login_follow(client, "leiro-me", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "Másikhoz Tartozó" not in body


def test_layout_shows_dual_cards(client):
    leiro = create_user("layout-leiro", "pw", role="leíró", screen_name="Layout")
    login_follow(client, "layout-leiro", "pw")

    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert 'class="row g-3 mt-3"' in body
    assert "Boncolások" in body
    assert "Vizsgálatok" in body


def test_investigation_case_number_links_to_investigation_detail(client):
    leiro = create_user("link-leiro", "pw", role="leíró", screen_name="Link")
    expert = create_user(
        "link-szak",
        "pw",
        role="szakértő",
        screen_name="Link szak",
        default_leiro_id=leiro.id,
    )
    inv = create_investigation(
        subject_name="Linkelt ügy",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
        case_number="INV-4242",
    )
    inv.case_id = 4242

    login_follow(client, "link-leiro", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert f'<a href="/investigations/{inv.id}">{inv.case_number}</a>' in body


def test_investigation_case_number_links_without_case_id(client):
    leiro = create_user("linkless-leiro", "pw", role="leíró", screen_name="Linkless")
    expert = create_user(
        "linkless-szak",
        "pw",
        role="szakértő",
        screen_name="Linkless szak",
        default_leiro_id=leiro.id,
    )
    inv = create_investigation(
        subject_name="Link nélküli ügy",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
        case_number="INV-1717",
    )

    login_follow(client, "linkless-leiro", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert f'<a href="/investigations/{inv.id}">{inv.case_number}</a>' in body


def test_leiro_placeholder_page_accessible(client):
    leiro = create_user("placeholder-leiro", "pw", role="leíró", screen_name="Holder")
    expert = create_user(
        "placeholder-szak",
        "pw",
        role="szakértő",
        screen_name="Holder szak",
        default_leiro_id=leiro.id,
    )
    inv = create_investigation(
        subject_name="Placeholder vizsgálat",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
    )

    login_follow(client, "placeholder-leiro", "pw")
    response = client.get(f"/investigations/{inv.id}/leiro/elvegzem")

    assert response.status_code == 200
    assert "Leíró — Vizsgálat munkalap" in response.get_data(as_text=True)
