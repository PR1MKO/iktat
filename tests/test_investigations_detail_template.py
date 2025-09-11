"""Tests for investigation detail template safety and rendering."""

import re
from pathlib import Path

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
