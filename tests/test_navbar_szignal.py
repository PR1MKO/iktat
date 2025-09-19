from tests.helpers import create_user, login, login_follow

BUTTON_TEXT = "Szakértő kijelölése"
BUTTON_HREF = 'href="/szignal_cases"'


def _login_and_fetch_page(client, username, password, *, target="/dashboard"):
    response = login_follow(client, username, password)
    if response.status_code != 200:
        response = client.get(target, follow_redirects=True)
    return response


def test_navbar_shows_szignal_assignment_link_for_szig(client, app):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
    with client:
        login(client, "szig-user", "pw")
        resp = client.get("/szignal_cases", follow_redirects=True)
        html = resp.get_data(as_text=True)
        assert BUTTON_TEXT in html
        assert BUTTON_HREF in html


def test_navbar_shows_szignal_assignment_link_for_legacy_szignalo(client, app):
    with app.app_context():
        create_user("legacy-szignalo", "pw", role="szignáló")
    with client:
        resp = _login_and_fetch_page(
            client, "legacy-szignalo", "pw", target="/szignal_cases"
        )
        html = resp.get_data(as_text=True)
        assert BUTTON_TEXT in html
        assert BUTTON_HREF in html


def test_navbar_hides_szignal_assignment_link_for_other_roles(client, app):
    roles = ["admin", "iroda", "szak", "leir", "penz", "toxi"]
    for idx, role in enumerate(roles):
        username = f"user-{idx}-{role}"
        with app.app_context():
            create_user(username, "pw", role=role)
        with client:
            resp = _login_and_fetch_page(client, username, "pw")
            html = resp.get_data(as_text=True)
            assert BUTTON_TEXT not in html
            assert BUTTON_HREF not in html
