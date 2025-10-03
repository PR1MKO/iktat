import re
from urllib.parse import urlparse

from tests.helpers import create_user, login


def test_cases_new_preserves_inputs_on_invalid_submit_prg(client, app):
    with app.app_context():
        create_user()

    with client:
        login(client, "admin", "secret")

        initial = client.get("/cases/new")
        assert initial.status_code == 200

        data = {
            "beerk_modja": "Email",
            "temp_id": "TMP-42",
            "deceased_name": "John Doe",
        }
        response = client.post("/cases/new", data=data, follow_redirects=False)
        assert response.status_code in (302, 303)
        redirected_path = urlparse(response.headers["Location"]).path
        assert redirected_path == "/cases/new"

        follow = client.get(response.headers["Location"])
        assert follow.status_code == 200
        html = follow.data.decode()

        assert "Típus, Intézmény neve kitöltése kötelező." in html
        assert re.search(r'name="temp_id"[^>]*value="TMP-42"', html)
        assert re.search(r'name="deceased_name"[^>]*value="John Doe"', html)
        assert re.search(r'<option value="Email"[^>]*selected', html)
        assert re.search(
            r'id="case_type"[\s\S]*?<option value=""[^>]*selected>-- Válasszon --</option>',
            html,
        )
