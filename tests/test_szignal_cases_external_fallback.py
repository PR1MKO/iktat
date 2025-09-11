import pytest

from app import db
from app.models import Case
from tests.helpers import create_user, login


def test_examinations_kulso_ugyirat_fallbacks_to_temp_id(app, client):
    """When external case number missing, show temp_id in examinations table."""
    with app.app_context():
        c = Case(case_number="B:0016/2025", external_case_number=None, temp_id="555666")
        db.session.add(c)
        db.session.commit()

    create_user("sig", "pw", role="szignáló")
    with client:
        login(client, "sig", "pw")
        resp = client.get("/szignal_cases")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        parts = html.split('id="examinations-unassigned"')[1].split(
            'id="examinations-with-expert"'
        )
        unassigned_html = parts[0]
        assert "555666" in unassigned_html
