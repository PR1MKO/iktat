from app import db
from app.models import Case
from tests.helpers import create_investigation, create_user, login


def test_szignal_cases_edit_button_links_to_case_assignment(app, client):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
        case = Case(
            case_number="CASE-WITH-EXPERT",
            deceased_name="Teszt Alany",
            status="szignálva",
            expert_1="Dr. Expert",
        )
        db.session.add(case)
        db.session.commit()
        case_id = case.id

    login(client, "szig-user", "pw")
    resp = client.get("/szignal_cases")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert f'href="/szignal_cases/{case_id}/assign"' in html


def test_szignal_cases_investigation_editor_links_to_assignment(app, client):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
        expert = create_user("expert-user", "pw", role="szakértő")
        investigation = create_investigation(
            case_number="INV-WITH-EXPERT",
            expert1_id=expert.id,
        )
        investigation_id = investigation.id

    login(client, "szig-user", "pw")
    resp = client.get("/szignal_cases")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert f'href="/investigations/{investigation_id}/assign"' in html
