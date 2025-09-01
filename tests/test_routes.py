import re
from pathlib import Path

from flask import url_for

from tests.helpers import create_user, login


def test_template_url_for_resolves(app):
    """Ensure all url_for references in templates resolve to actual endpoints."""
    endpoints = set()
    templates_dir = Path("app/templates")
    for path in templates_dir.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"url_for\(['\"]([\w\.]+)['\"]", text):
            endpoints.add(match.group(1))
    with app.test_request_context():
        for ep in endpoints:
            rules = [r for r in app.url_map.iter_rules() if r.endpoint == ep]
            assert rules, f"Unknown endpoint referenced in templates: {ep}"
            kwargs = {arg: "1" for arg in rules[0].arguments}
            url_for(ep, **kwargs)


def test_no_duplicate_routes(app):
    """Confirm critical routes are not duplicated."""
    rules = list(app.url_map.iter_rules())
    cases_rules = [r for r in rules if r.rule == "/cases"]
    assert len(cases_rules) == 1, "'/cases' should have exactly one rule"
    cert_rules = [
        r for r in rules if r.rule == "/ugyeim/<int:case_id>/generate_certificate"
    ]
    assert len(cert_rules) == 1, "Certificate generation route should be unique"


def test_cases_route_returns_response(app, client):
    """'/cases' should return a valid response when logged in."""
    with app.app_context():
        create_user("admin", "secret")
    login(client, "admin", "secret")
    resp = client.get("/cases")
    assert resp.status_code not in (404, 500)
