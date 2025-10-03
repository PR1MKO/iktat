from datetime import date

from app import db
from app.investigations.models import Investigation, InvestigationChangeLog
from app.models import Case, ChangeLog


def _collect_new_logs(query, baseline_ids):
    return [entry for entry in query if entry.id not in baseline_ids]


def test_case_insert_logs_all_columns(app):
    with app.app_context():
        case = Case(
            case_number="LOG-CASE-1",
            deceased_name="Jane Doe",
            case_type="demo",
            status="open",
        )
        db.session.add(case)
        db.session.commit()

        logs = ChangeLog.query.filter_by(case_id=case.id).all()
        fields = {log.field_name for log in logs}
        for expected in {"case_number", "deceased_name", "case_type", "status"}:
            assert expected in fields
        for log in logs:
            if log.field_name in {
                "case_number",
                "deceased_name",
                "case_type",
                "status",
            }:
                assert log.old_value == "∅"
                assert log.edited_by == "system"


def test_case_update_logs_changed_columns_only(app):
    with app.app_context():
        case = Case(
            case_number="LOG-CASE-2",
            status="new",
            institution_name="Orig",
        )
        db.session.add(case)
        db.session.commit()

        baseline_ids = {
            log.id for log in ChangeLog.query.filter_by(case_id=case.id).all()
        }

        case.status = "closed"
        case.institution_name = "Updated"
        db.session.commit()

        updated_logs = _collect_new_logs(
            ChangeLog.query.filter_by(case_id=case.id).all(), baseline_ids
        )
        fields = {log.field_name for log in updated_logs}
        assert fields == {"status", "institution_name"}
        for log in updated_logs:
            assert log.old_value != log.new_value
            assert log.edited_by == "system"


def test_investigation_insert_and_update_logs(app):
    with app.app_context():
        inv = Investigation(
            case_number="INV-9000",
            subject_name="Subject",
            maiden_name="Maiden",
            investigation_type="Type",
            mother_name="Mother",
            birth_place="City",
            birth_date=date(2000, 1, 1),
            taj_number="123456789",
            residence="Address",
            citizenship="HU",
            institution_name="Inst",
        )
        db.session.add(inv)
        db.session.commit()

        logs = InvestigationChangeLog.query.filter_by(investigation_id=inv.id).all()
        assert any(log.field_name == "case_number" for log in logs)
        baseline_ids = {log.id for log in logs}

        inv.subject_name = "Updated Subject"
        inv.institution_name = "Updated Inst"
        db.session.commit()

        updated_logs = _collect_new_logs(
            InvestigationChangeLog.query.filter_by(investigation_id=inv.id).all(),
            baseline_ids,
        )
        fields = {log.field_name for log in updated_logs}
        assert fields == {"subject_name", "institution_name"}
        for log in updated_logs:
            assert log.old_value != log.new_value
            assert log.edited_by == 0


def test_changelog_truncates_long_values(app):
    with app.app_context():
        payload = "X" * 1200
        case = Case(case_number="LOG-CASE-TRUNC", deceased_name=payload)
        db.session.add(case)
        db.session.commit()

        log = (
            ChangeLog.query.filter_by(case_id=case.id, field_name="deceased_name")
            .order_by(ChangeLog.id)
            .first()
        )
        assert log is not None
        assert log.new_value.startswith("X" * 500)
        assert log.new_value.endswith("…[+700]")
        assert len(log.new_value) <= 520


def test_cross_bind_logging_isolated(app):
    with app.app_context():
        before_investigation_logs = InvestigationChangeLog.query.count()
        case = Case(case_number="LOG-CASE-3")
        db.session.add(case)
        db.session.commit()
        assert InvestigationChangeLog.query.count() == before_investigation_logs

        inv = Investigation(
            case_number="INV-9001",
            subject_name="Subject",
            maiden_name="Maiden",
            investigation_type="Type",
            mother_name="Mother",
            birth_place="City",
            birth_date=date(2000, 1, 1),
            taj_number="987654321",
            residence="Address",
            citizenship="HU",
            institution_name="Inst",
        )
        db.session.add(inv)
        db.session.commit()

        assert (
            InvestigationChangeLog.query.filter_by(investigation_id=inv.id).count() > 0
        )
        assert ChangeLog.query.filter_by(case_id=case.id).count() > 0
