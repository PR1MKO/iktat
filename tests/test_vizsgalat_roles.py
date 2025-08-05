from datetime import datetime
import re

from app.models import Case, ChangeLog, db
from app.utils.time_utils import BUDAPEST_TZ
from tests.helpers import create_user, login


def test_iroda_can_order_and_szakerto_sees_preselected(client, app, monkeypatch):
    with app.app_context():
        create_user('clerk', 'pw', 'iroda')
        create_user('doc', 'pw', 'szakértő')
        case = Case(case_number='R1', expert_1='doc')
        db.session.add(case)
        db.session.commit()
        cid = case.id

    t1 = datetime(2024, 1, 2, 8, 0, tzinfo=BUDAPEST_TZ)
    monkeypatch.setattr('app.routes.now_local', lambda: t1)
    with client:
        login(client, 'clerk', 'pw')
        data = {'alkohol_ver_ordered': 'on', 'alkohol_ver': '1'}
        resp = client.post(f'/ugyeim/{cid}/vizsgalat_elrendelese', data=data)
        assert resp.status_code == 302
        assert resp.headers['Location'] == f'/cases/{cid}/edit'

    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.alkohol_ver_ordered is True
        assert case.alkohol_ver == '1'
        first_line = case.tox_orders.strip().splitlines()[0]
        assert 'clerk' in first_line

    with client:
        login(client, 'doc', 'pw')
        resp = client.get(f'/ugyeim/{cid}/vizsgalat_elrendelese')
        html = resp.get_data(as_text=True)
        assert re.search(r'id="alkohol_ver_ordered"[^>]*checked disabled', html)
        t2 = datetime(2024, 1, 2, 9, 0, tzinfo=BUDAPEST_TZ)
        monkeypatch.setattr('app.routes.now_local', lambda: t2)
        data2 = {'tox_cpk_ordered': 'on', 'tox_cpk': '2'}
        resp2 = client.post(f'/ugyeim/{cid}/vizsgalat_elrendelese', data=data2)
        assert resp2.status_code == 302
        assert resp2.headers['Location'] == f'/ugyeim/{cid}/elvegzem'

    with app.app_context():
        case = db.session.get(Case, cid)
        lines = case.tox_orders.strip().splitlines()
        assert len(lines) == 2
        assert 'clerk' in lines[0]
        assert 'doc' in lines[1]
        logs = ChangeLog.query.filter_by(case_id=cid, field_name='tox_orders').order_by(ChangeLog.id).all()
        assert logs[0].new_value == lines[0]
        assert logs[0].edited_by == 'clerk'
        assert logs[1].new_value == lines[1]
        assert logs[1].edited_by == 'doc'


def test_create_and_edit_pages_show_button_for_iroda(client, app):
    with app.app_context():
        create_user('clerk', 'pw', 'iroda')
        case = Case(case_number='B1')
        db.session.add(case)
        db.session.commit()
        cid = case.id

    with client:
        login(client, 'clerk', 'pw')
        resp_new = client.get('/cases/new')
        assert 'Vizsgálatok elrendelése' in resp_new.get_data(as_text=True)

        resp_edit = client.get(f'/cases/{cid}/edit')
        html_edit = resp_edit.get_data(as_text=True)
        assert f'/ugyeim/{cid}/vizsgalat_elrendelese' in html_edit
        assert 'Vizsgálatok elrendelése' in html_edit