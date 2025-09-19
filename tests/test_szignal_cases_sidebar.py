from tests.helpers import create_user, login


def test_szignal_cases_renders_sidebar_for_szigi_user(client, app):
    with app.app_context():
        create_user("szig-member", "pw", role="szig")

    with client:
        login(client, "szig-member", "pw")
        response = client.get("/szignal_cases", follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="sidebar"' in html
