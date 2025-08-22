from app.models import Case, db
from tests.helpers import create_user, login, create_investigation


def test_penzugy_dashboard_read_only(client, app):
    """Pénzügy dashboard lists cases and investigations without action buttons."""
    with app.app_context():
        create_user('fin', 'pw', role='pénzügy')
        case = Case(case_number='B:1000/2025')
        db.session.add(case)
        create_investigation()
        db.session.commit()
    with client:
        login(client, 'fin', 'pw')
        resp = client.get('/dashboard/penzugy')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'Ügyek' in html and 'Vizsgálatok' in html
        for forbidden in ['Szerkeszt', 'Feltölt', 'Hozzárendel', 'Megjegyz']:
            assert forbidden not in html


def test_non_penzugy_cannot_access_dashboard(client, app):
    with app.app_context():
        create_user('io', 'pw', role='iroda')
    with client:
        login(client, 'io', 'pw')
        resp = client.get('/dashboard/penzugy')
        assert resp.status_code in (302, 403)