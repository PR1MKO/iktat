from app import db
from app.models import Case
from tests.helpers import create_user, login


def test_boncszam_links_present_in_both_case_tables(app, client):
    with app.app_context():
        create_user("signer", "pw", role="szignáló")
        unassigned_case = Case(
            case_number="C-UNASSIGNED",
            status="beérkezett",
            deceased_name="Unassigned",
        )
        with_expert_case = Case(
            case_number="C-WITH-EXPERT",
            status="beérkezett",
            deceased_name="Assigned",
            expert_1="Dr. Expert",
        )
        db.session.add_all([unassigned_case, with_expert_case])
        db.session.commit()

        unassigned_id = unassigned_case.id
        unassigned_number = unassigned_case.case_number
        with_expert_id = with_expert_case.id
        with_expert_number = with_expert_case.case_number

    login(client, "signer", "pw")
    resp = client.get("/szignal_cases")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert f'<a href="/cases/{unassigned_id}">{unassigned_number}</a>' in html
    assert f'<a href="/cases/{with_expert_id}">{with_expert_number}</a>' in html
