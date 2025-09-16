from datetime import datetime, timedelta, timezone

from app.models import Case, ChangeLog, db
from app.routes import append_note


def test_note_changelog_records_incrementally(app, monkeypatch):
    base_time = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routes.now_utc", lambda: base_time)
    with app.app_context():
        case = Case(case_number="NOTE1")
        db.session.add(case)
        db.session.commit()

        first = append_note(case, "first", author="U1")
        db.session.commit()

        logs = ChangeLog.query.filter_by(case_id=case.id, field_name="notes").all()
        assert len(logs) == 1
        assert logs[0].new_value == first

        monkeypatch.setattr(
            "app.routes.now_utc", lambda: base_time + timedelta(minutes=1)
        )
        second = append_note(case, "second", author="U1")
        db.session.commit()

        logs = (
            ChangeLog.query.filter_by(case_id=case.id, field_name="notes")
            .order_by(ChangeLog.id)
            .all()
        )
        assert len(logs) == 2
        assert logs[1].new_value == second
        assert logs[0].new_value != logs[1].new_value


def test_duplicate_note_entries_create_separate_logs(app, monkeypatch):
    base_time = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.routes.now_utc", lambda: base_time)
    with app.app_context():
        case = Case(case_number="NOTE2")
        db.session.add(case)
        db.session.commit()

        first = append_note(case, "repeat", author="U1")
        db.session.commit()

        append_note(case, "repeat", author="U1")
        db.session.commit()

        logs = (
            ChangeLog.query.filter_by(case_id=case.id, field_name="notes")
            .order_by(ChangeLog.id)
            .all()
        )
        assert len(logs) == 2
        assert logs[0].new_value == logs[1].new_value == first
