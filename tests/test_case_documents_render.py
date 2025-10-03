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
    assert '<div class="card-header fw-bold">Adatok</div>' in html
    assert '<button type="submit" class="btn btn-primary" disabled' in html


def test_iroda_access_and_next_requires_upload(client, app):
    from io import BytesIO

    from app import db
    from app.models import Case, User
    from tests.utils import login

    with app.app_context():
        iroda = User(username="iroda1", screen_name="iroda1", role="iroda")
        iroda.set_password("secret")
        case = Case(case_number="C2", external_case_number="EXT2")
        db.session.add_all([iroda, case])
        db.session.commit()
        cid = case.id

    login(client, "iroda1", "secret")

    resp = client.post(
        f"/cases/{cid}/documents",
        data={"tox_ordered": "y"},
        follow_redirects=True,
    )
    html = resp.get_data(as_text=True)
    assert "Legalább 1 fájl feltöltése kötelező a folytatáshoz." in html

    upload_resp = client.post(
        f"/cases/{cid}/upload",
        data={
            "category": "jegyzőkönyv",
            "file": (BytesIO(b"dummy"), "doc1.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert upload_resp.status_code == 200

    next_resp = client.post(
        f"/cases/{cid}/documents",
        data={"tox_ordered": "y"},
        follow_redirects=False,
    )
    assert next_resp.status_code == 302
    assert next_resp.headers["Location"].endswith(f"/cases/{cid}/edit")
