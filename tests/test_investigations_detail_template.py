"""Tests for investigation detail template safety and rendering."""

import re
from pathlib import Path

from app import db
from tests.helpers import create_investigation, create_user, login


def test_no_django_style_include_mapping():
    """Ensure templates avoid Django-style `include ... with ...` mapping."""
    templates_dir = Path("app/templates")
    pattern = re.compile(r"{%\s*include\b[^%]*\bwith\b[^%]*%}")
    offenders = []
    for path in templates_dir.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(path.as_posix())
    assert not offenders, f"Django-style include mappings found: {offenders}"


def test_investigation_detail_page_renders_for_szig(app, client):
    """Detail page should render for an szig user without template errors."""
    create_user("szig_user", "pw", role="szig")
    investigation = create_investigation()
    with client:
        login(client, "szig_user", "pw")
        resp = client.get(f"/investigations/{investigation.id}")
        assert resp.status_code == 200


def test_detail_template_shows_required_labels(app, client):
    create_user("szig_user", "pw", role="szig")
    investigation = create_investigation(
        assignment_type="INTEZETI", investigation_type="type1"
    )
    with client:
        login(client, "szig_user", "pw")
        resp = client.get(f"/investigations/{investigation.id}")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Végrehajtás módja" in html
        assert "Vizsgálat típusa" in html


def test_detail_shows_expert_screen_name_and_describer_row(app, client):
    viewer = create_user("szig_user", "pw", role="szig")
    expert = create_user(
        "expert_user",
        "pw",
        role="szak",
        screen_name="Dr. Szak Screen",
    )
    describer = create_user(
        "describer_user",
        "pw",
        role="leir",
        screen_name="Leíró Screen",
    )
    investigation = create_investigation(
        assignment_type="SZAKÉRTŐI",
        assigned_expert_id=expert.id,
        expert1_id=expert.id,
        describer_id=describer.id,
    )
    with client:
        login(client, viewer.username, "pw")
        resp = client.get(f"/investigations/{investigation.id}")
    html = resp.get_data(as_text=True)
    assert "Szakértő" in html
    assert "Dr. Szak Screen" in html
    assert "Leíró" in html
    assert "Leíró Screen" in html


def test_detail_fallbacks_to_expert_default_leiro_when_none_set(app, client):
    viewer = create_user("szig_user", "pw", role="szig")
    expert = create_user(
        "expert_user",
        "pw",
        role="szak",
        screen_name="Dr. Szak Screen",
    )
    default_leiro = create_user(
        "default_leiro",
        "pw",
        role="leir",
        screen_name="Default Leíró",
    )
    expert.default_leiro_id = default_leiro.id
    db.session.commit()
    investigation = create_investigation(
        assignment_type="SZAKÉRTŐI",
        assigned_expert_id=expert.id,
        expert1_id=expert.id,
    )
    with client:
        login(client, viewer.username, "pw")
        resp = client.get(f"/investigations/{investigation.id}")
    html = resp.get_data(as_text=True)
    assert "Leíró" in html
    assert "Default Leíró" in html


def test_detail_shows_dash_when_no_describer_and_no_default(app, client):
    viewer = create_user("szig_user", "pw", role="szig")
    expert = create_user(
        "expert_user",
        "pw",
        role="szak",
        screen_name="Dr. Szak Screen",
    )
    investigation = create_investigation(
        assignment_type="SZAKÉRTŐI",
        assigned_expert_id=expert.id,
        expert1_id=expert.id,
    )
    with client:
        login(client, viewer.username, "pw")
        resp = client.get(f"/investigations/{investigation.id}")
    html = resp.get_data(as_text=True)
    assert "Leíró" in html
    assert "–" in html
