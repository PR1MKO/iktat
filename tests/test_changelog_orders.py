from app.models import Case, ChangeLog, db


def test_tox_order_changelog_records_incrementally(app):
    with app.app_context():
        case = Case(case_number="ORDER1")
        db.session.add(case)
        db.session.commit()

        first = "Alkohol vizelet: 1 rendelve: 2024-01-01 10:00 - U1"
        case.tox_orders = first
        db.session.commit()

        logs = ChangeLog.query.filter_by(case_id=case.id, field_name="tox_orders").all()
        assert len(logs) == 1
        assert logs[0].new_value == first

        second = "Vese - Spec fest rendelve: 2024-01-02 11:00 - U1"
        case.tox_orders = case.tox_orders + "\n" + second
        db.session.commit()

        logs = ChangeLog.query.filter_by(case_id=case.id, field_name="tox_orders").order_by(ChangeLog.id).all()
        assert len(logs) == 2
        assert logs[1].new_value == second
        assert logs[0].new_value != logs[1].new_value
		