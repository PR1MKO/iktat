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
    create_investigation(
        subject_name="Minta Alany",
        status="szignálva",
        expert1_id=expert.id,
        describer_id=None,
    )

    login_follow(client, "leiro-default", "pw")
    body = client.get("/leiro/ugyeim").get_data(as_text=True)

    assert "Minta Alany" in body


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
