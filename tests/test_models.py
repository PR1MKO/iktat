from datetime import datetime

from app.models import Case, User, db
from app.utils.time_utils import BUDAPEST_TZ


def test_create_user(app):
    with app.app_context():
        user = User(username="testuser", role="admin")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

        loaded = User.query.filter_by(username="testuser").first()
        assert loaded is not None
        assert loaded.check_password("testpass")


def test_case_formatted_deadline_and_overdue(app):
    with app.app_context():
        past = datetime(2020, 1, 1, tzinfo=BUDAPEST_TZ)
        case = Case(case_number="TESTX", deadline=past)
        db.session.add(case)
        db.session.commit()

        expected = past.astimezone(BUDAPEST_TZ).strftime("%Y-%m-%d")
        assert case.formatted_deadline == expected
