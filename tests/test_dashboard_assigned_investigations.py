from app.investigations.models import Investigation
from tests.helpers import create_investigation, create_user, login


def test_assigned_investigation_visible_on_dashboard(client, app):
    with app.app_context():
        user = create_user("szak1", "pw", role="szakértő")
        inv = create_investigation(
            case_number="V:0009/2025",
            assignment_type="SZAKÉRTŐI",
            assigned_expert_id=user.id,
        )
        inv_id = inv.id

    with client:
        login(client, "szak1", "pw")
        resp = client.get("/dashboard")
        assert b"V:0009/2025" in resp.data
        assert b"has been signalled to you" in resp.data
        assert f"/investigations/{inv_id}/view".encode() in resp.data


def test_auto_assigned_investigation_immediately_visible(client, app):
    with app.app_context():
        create_user()  # admin
        expert = create_user("szak2", "pw", role="szakértő")
        expert_id = expert.id
    with client:
        login(client, "admin", "secret")
        data = {
            "subject_name": "Teszt Alany",
            "mother_name": "Teszt Anya",
            "birth_place": "Budapest",
            "birth_date": "2000-01-02",
            "taj_number": "123456789",
            "residence": "Cím",
            "citizenship": "magyar",
            "institution_name": "Intézet",
            "investigation_type": "type1",
            "external_case_number": "EXT1",
            "assignment_type": "SZAKÉRTŐI",
            "assigned_expert_id": expert_id,
        }
        resp = client.post("/investigations/new", data=data, follow_redirects=False)
        assert resp.status_code == 302
        client.get("/logout", follow_redirects=False)
        login(client, "szak2", "pw")
        with app.app_context():
            inv = Investigation.query.order_by(Investigation.id.desc()).first()
            case_number = inv.case_number
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        page = resp.get_data(as_text=True)
        assert case_number in page
        assert "has been signalled to you" in page
