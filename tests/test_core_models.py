from datetime import datetime, timedelta, date
import pytz

from app.models import User, Case, UploadedFile, ChangeLog, db


def test_user_creation_and_password(app):
    with app.app_context():
        user = User(username="alice", role="admin")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()

        loaded = User.query.filter_by(username="alice").first()
        assert loaded is not None
        assert loaded.password_hash != "secret"
        assert loaded.check_password("secret")
        assert not loaded.check_password("wrong")


def test_user_roles(app):
    with app.app_context():
        admin = User(username="admin1", role="admin")
        admin.set_password("a")
        regular = User(username="bob", role="szakértő")
        regular.set_password("b")
        db.session.add_all([admin, regular])
        db.session.commit()

        assert User.query.filter_by(role="admin").count() == 1
        assert User.query.filter_by(role="szakértő").first().username == "bob"


def test_case_creation_full(app):
    with app.app_context():
        case = Case(
            case_number="CASE1",
            deceased_name="John Doe",
            case_type="test",
            status="open",
            institution_name="Inst",
            external_case_number="E1",
            birth_date=date(2000, 1, 1),
            deadline=datetime.now(pytz.UTC) + timedelta(days=1),
        )
        db.session.add(case)
        db.session.commit()

        loaded = Case.query.filter_by(case_number="CASE1").first()
        assert loaded.deceased_name == "John Doe"
        assert isinstance(loaded.registration_time, datetime)


def test_case_defaults(app):
    with app.app_context():
        case = Case(case_number="CASE2")
        db.session.add(case)
        db.session.commit()

        loaded = db.session.get(Case, case.id)
        assert loaded.status == "new"
        assert loaded.registration_time is not None


def test_uploaded_file_association(app):
    with app.app_context():
        case = Case(case_number="CASE4")
        db.session.add(case)
        db.session.commit()

        uf = UploadedFile(case_id=case.id, filename="report.txt", uploader="alice", category="egyéb")
        db.session.add(uf)
        db.session.commit()

        loaded_case = db.session.get(Case, case.id)
        assert len(loaded_case.uploaded_file_records) == 1
        rec = loaded_case.uploaded_file_records[0]
        assert rec.filename == "report.txt"
        assert rec.uploader == "alice"
        assert rec.upload_time is not None


def test_change_log_created_on_update(app):
    with app.app_context():
        case = Case(case_number="CASE5", deceased_name="Old")
        db.session.add(case)
        db.session.commit()

        case.deceased_name = "New"
        db.session.commit()

        logs = ChangeLog.query.filter_by(case_id=case.id).all()
        assert len(logs) == 1
        log = logs[0]
        assert log.field_name == "deceased_name"
        assert log.new_value == "New"
        assert log.edited_by == "system"
        assert log.case == case

