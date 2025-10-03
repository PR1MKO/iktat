import re


def test_new_case_number_format(client, app):
    with app.app_context():
        from tests.helpers import create_user, login

        create_user()
    with client:
        login(client, "admin", "secret")
        resp = client.post(
            "/cases/new",
            data={
                "case_type": "t",
                "beerk_modja": "Email",
                "temp_id": "TMP",
                "institution_name": "Clinic",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
    with app.app_context():
        from app.models import Case

        c = Case.query.order_by(Case.id.desc()).first()
        assert re.match(r"^B:\d{4}/\d{4}$", c.case_number)
