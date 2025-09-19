"""CSP regression tests for investigations UI."""

import re

from tests.helpers import create_user, login


def test_investigations_new_includes_nonce_on_toggle_script(client):
    create_user("iroda", "pw", "iroda")
    login(client, "iroda", "pw")

    resp = client.get("/investigations/new")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    script_match = re.search(
        r'<script[^>]+src="[^"]*/js/investigations_toggle\.js"[^>]*>',
        html,
        re.IGNORECASE,
    )
    assert (
        script_match
    ), "investigations_toggle.js must be included on /investigations/new"
    assert re.search(r'nonce="[^"]+"', script_match.group(0)), (
        "investigations_toggle.js must include a CSP nonce",
    )
