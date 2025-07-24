import pytz
from datetime import datetime

from app.models import Case, db
from tests.helpers import create_user, login


def test_empty_tox_field_is_logged(client, app, monkeypatch):
    with app.app_context():
        create_user('doc', 'pw', 'szakértő')
        case = Case(case_number='T1', expert_1='doc')
        db.session.add(case)
        db.session.commit()
        cid = case.id

    fixed = datetime(2024, 1, 1, 12, 0, tzinfo=pytz.UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr('app.routes.datetime', FixedDateTime)

    with client:
        login(client, 'doc', 'pw')
        data = {
            'alkohol_vizelet_ordered': 'on',
            'alkohol_vizelet': ''
        }
        resp = client.post(f'/ugyeim/{cid}/vizsgalat_elrendelese', data=data)
        assert resp.status_code == 302

    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.alkohol_vizelet_ordered is True
        assert case.tox_orders.strip() == f'Alkohol vizelet rendelve: {fixed.strftime("%Y-%m-%d %H:%M")} – doc'		

