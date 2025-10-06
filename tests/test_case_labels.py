import io
import re

from flask_login import login_user, logout_user

from app.models import Case, ChangeLog, UploadedFile, db
from app.utils.user_display import user_display_name
from tests.helpers import create_user, login_follow


def test_user_display_name_prefers_full_name():
    class Dummy:
        def __init__(self, full_name=None, screen_name=None, username=None):
            self.full_name = full_name
            self.screen_name = screen_name
            self.username = username

    dummy = Dummy(full_name="Full Name", screen_name="Screen", username="user")
    assert user_display_name(dummy) == "Full Name"

    dummy.full_name = ""
    assert user_display_name(dummy) == "Screen"

    dummy.screen_name = None
    assert user_display_name(dummy) == "user"

    assert user_display_name(None) == "system"


def test_changelog_uses_full_name_and_formats_timestamp(client, app):
    with app.app_context():
        user = create_user("log_user", "secret", "iroda", full_name="Log Lady")
        case = Case(case_number="CASELOG", deceased_name="Old")
        db.session.add(case)
        db.session.commit()
        case_id = case.id

        with app.test_request_context():
            login_user(user)
            case.deceased_name = "New"
            db.session.commit()
            logout_user()

        log = (
            ChangeLog.query.filter_by(case_id=case_id, field_name="deceased_name")
            .order_by(ChangeLog.id.desc())
            .first()
        )
        assert log is not None
        assert log.edited_by == "Log Lady"

    login_follow(client, "log_user", "secret")
    resp = client.get(f"/cases/{case_id}")
    html = resp.get_data(as_text=True)
    assert "Log Lady" in html
    assert re.search(r"\d{4}/\d{2}/\d{2} \d{2}:\d{2} — Log Lady", html)
    assert "[Log Lady" not in html


def test_uploaded_files_display_full_name_and_timestamp(client, app):
    with app.app_context():
        user = create_user("upload_user", "secret", "admin", full_name="Uploader U.")
        case = Case(case_number="CASEUP")
        db.session.add(case)
        db.session.commit()
        case_id = case.id

    login_follow(client, "upload_user", "secret")
    data = {
        "category": "jegyzőkönyv",
        "file": (io.BytesIO(b"content"), "file.pdf"),
    }
    resp = client.post(
        f"/cases/{case_id}/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)

    with app.app_context():
        rec = (
            UploadedFile.query.filter_by(case_id=case_id, filename="file.pdf")
            .order_by(UploadedFile.id.desc())
            .first()
        )
        assert rec is not None
        assert rec.uploader == "Uploader U."

    resp = client.get(f"/cases/{case_id}")
    html = resp.get_data(as_text=True)
    assert "file.pdf" in html
    assert "Uploader U." in html
    assert re.search(r"Uploader U\. · \d{4}/\d{2}/\d{2} \d{2}:\d{2}", html)
    assert "[Uploader U." not in html


def test_add_note_stamps_full_name(client, app):
    with app.app_context():
        user = create_user("note_user", "secret", "admin", full_name="Note Nora")
        case = Case(case_number="CASENOTE")
        db.session.add(case)
        db.session.commit()
        case_id = case.id

    login_follow(client, "note_user", "secret")
    resp = client.post(
        f"/cases/{case_id}/add_note",
        json={"new_note": "Fontos"},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert "Note Nora" in payload["html"]
    assert re.search(r"\[\d{4}/\d{2}/\d{2} \d{2}:\d{2} – Note Nora]", payload["html"])

    with app.app_context():
        updated = db.session.get(Case, case_id)
        assert updated is not None
        assert "Note Nora" in (updated.notes or "")
        note_log = (
            ChangeLog.query.filter_by(case_id=case_id, field_name="notes")
            .order_by(ChangeLog.id.desc())
            .first()
        )
        assert note_log is not None
        assert note_log.edited_by == "Note Nora"
