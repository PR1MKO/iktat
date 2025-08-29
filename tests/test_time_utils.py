import pytz
from datetime import datetime

from app.utils.time_utils import BUDAPEST_TZ
from app.routes import append_note
from app.models import Case, db


def test_append_note_uses_local_time(monkeypatch, app):
    fixed_dt = datetime(2021, 1, 2, 3, 4, tzinfo=BUDAPEST_TZ)
    monkeypatch.setattr('app.routes.now_local', lambda: fixed_dt)
    with app.app_context():
        case = Case(case_number='TEST')
        db.session.add(case)
        db.session.commit()
        note = append_note(case, 'hello', author='Tester')
        assert '[2021-01-02 03:04' in note
        assert case.notes.strip() == note


def test_localtime_filter(app):
    with app.app_context():
        filt = app.jinja_env.filters['localtime']
        dt = BUDAPEST_TZ.localize(datetime(2021, 1, 1, 12, 0))
        expected = dt.astimezone(BUDAPEST_TZ).strftime('%Y-%m-%d %H:%M')
        assert filt(dt) == expected
