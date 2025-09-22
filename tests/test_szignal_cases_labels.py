from tests.helpers import create_investigation, create_user, login


def test_vizsgalat_button_label_is_szerkesztes(app, client):
    with app.app_context():
        create_user("szig-user", "pw", role="szig")
        expert = create_user("expert-user", "pw", role="szakértő")
        create_investigation(case_number="INV-WITH-EXPERT", expert1_id=expert.id)

    login(client, "szig-user", "pw")
    response = client.get("/szignal_cases")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Szerkesztő" not in html
    assert "Szerkesztés" in html
