from tests.helpers import create_investigation, create_user, login


def test_szig_user_can_open_assignment_pages(app, client):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
        case = create_case()
        investigation = create_investigation(case_number="INV-ACCESS")
        case_id = case.id
        investigation_id = investigation.id

    login(client, "szig-user", "pw")

    resp_case = client.get(f"/szignal_cases/{case_id}/assign")
    assert resp_case.status_code in (200, 302)

    resp_investigation = client.get(f"/investigations/{investigation_id}/assign")
    assert resp_investigation.status_code in (200, 302)


def create_case():
    from app import db
    from app.models import Case

    case = Case(
        case_number="CASE-ACCESS",
        deceased_name="Elhunyt",
        status="beérkezett",
    )
    db.session.add(case)
    db.session.commit()
    return case
