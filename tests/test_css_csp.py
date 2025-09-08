import re

from app.models import Case, db
from tests.helpers import create_user, login


def _assert_no_external_css_and_no_inline_style(html: str) -> None:
    assert re.search(r'<link[^>]+href="http', html) is None
    assert re.search(r"<style[^>]*>", html) is None


def test_login_csp_and_css(client):
    r = client.get("/login")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "style-src 'self'" in csp
    m = re.search(r"style-src([^;]+)", csp)
    assert m and "http" not in m.group(1)
    html = r.get_data(as_text=True)
    _assert_no_external_css_and_no_inline_style(html)
    assert "/static/css/bootstrap.min.css" in html
    assert "/static/css/bootstrap-icons.css" in html
    assert "/static/css/custom.css" in html


def test_tox_doc_form_extends_styles_block(client, app):
    with app.app_context():
        create_user("tox", "pw", role="toxi")
        case = Case(case_number="B:0001/2025", anyja_neve="Teszt Anyja")
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    with client:
        login(client, "tox", "pw")
        r = client.get(f"/cases/{case_id}/tox_doc_form")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "style-src 'self'" in csp
    m = re.search(r"style-src([^;]+)", csp)
    assert m and "http" not in m.group(1)
    html = r.get_data(as_text=True)
    _assert_no_external_css_and_no_inline_style(html)
    assert "/static/css/bootstrap.min.css" in html
    assert "/static/css/bootstrap-icons.css" in html
    assert "/static/css/custom.css" in html
    assert "/static/css/tox_doc_form.css" in html
