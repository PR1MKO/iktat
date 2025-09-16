from datetime import datetime, timezone

from app.models import Case, db
from app.routes import append_note


def test_append_note_uses_local_time(monkeypatch, app):
    fixed_dt = datetime(2021, 1, 2, 3, 4, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routes.now_utc", lambda: fixed_dt)
    with app.app_context():
        case = Case(case_number="TEST")
        db.session.add(case)
        db.session.commit()
        note = append_note(case, "hello", author="Tester")
        assert "[2021/01/02 04:04" in note
        assert case.notes.strip() == note
