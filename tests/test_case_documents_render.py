def test_case_documents_renders_and_category_required(client, app):
    from app import db
    from app.models import Case, User

    # setup
    with app.app_context():
        admin = User(username="admin_render", screen_name="admin_render", role="admin")
        admin.set_password("secret")
        db.session.add(admin)
        c = Case(case_number="C1", external_case_number="EXT1")
        db.session.add(c)
        db.session.commit()
        cid = c.id
    # login
    from tests.utils import login as _login

    _login(client, "admin_render", "secret")
    # exercise
    resp = client.get(f"/cases/{cid}/documents")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'form id="file-upload-form"' in html
    assert '<select name="category"' in html and "required" in html
