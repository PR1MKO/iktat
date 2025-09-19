from __future__ import annotations

import re

from tests.helpers import create_user, login

LINK_TEXT = "Szakértő kijelölése"
LINK_HREF = 'href="/szignal_cases"'
_SIDEBAR_RE = re.compile(r'<nav[^>]+id="sidebar"[^>]*>(?P<body>.*?)</nav>', re.S)


def _login_and_fetch_page(client, username, password, *, target="/"):
    login(client, username, password)
    return client.get(target, follow_redirects=True)


def _extract_sidebar(html: str) -> str:
    match = _SIDEBAR_RE.search(html)
    assert match, "Sidebar navigation not found in response HTML"
    return match.group("body")


def _assert_link_precedes_home(sidebar_html: str) -> None:
    home_index = sidebar_html.find("KEZDŐLAP")
    assert home_index != -1, "Sidebar missing KEZDŐLAP entry"
    assert sidebar_html.find(LINK_TEXT) < home_index


def test_sidebar_shows_szignal_link_for_szig(client, app):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
    with client:
        resp = _login_and_fetch_page(client, "szig-user", "pw")
        html = resp.get_data(as_text=True)
        sidebar = _extract_sidebar(html)
        assert LINK_TEXT in sidebar
        assert LINK_HREF in sidebar
        _assert_link_precedes_home(sidebar)


def test_sidebar_shows_szignal_link_for_legacy_szignalo(client, app):
    with app.app_context():
        create_user("legacy-szignalo", "pw", role="szignáló")
    with client:
        resp = _login_and_fetch_page(client, "legacy-szignalo", "pw")
        html = resp.get_data(as_text=True)
        sidebar = _extract_sidebar(html)
        assert LINK_TEXT in sidebar
        assert LINK_HREF in sidebar
        _assert_link_precedes_home(sidebar)


def test_sidebar_hides_szignal_link_for_other_roles(client, app):
    roles = ["admin", "iroda", "szak", "leir", "penz", "toxi"]
    for idx, role in enumerate(roles):
        username = f"user-{idx}-{role}"
        with app.app_context():
            create_user(username, "pw", role=role)
        with client:
            resp = _login_and_fetch_page(client, username, "pw")
            html = resp.get_data(as_text=True)
            sidebar = _extract_sidebar(html)
            assert LINK_TEXT not in sidebar
            assert LINK_HREF not in sidebar
