from datetime import datetime

from app.models import Case, UploadedFile, ChangeLog, db
from app.utils.time_utils import BUDAPEST_TZ
from tests.helpers import create_user, login


def test_tox_view_unlocks_editing(client, app, monkeypatch):
    with app.app_context():
        create_user('doc', 'pw', 'szakértő')
        case = Case(case_number='T1', expert_1='doc', tox_ordered=True)
        db.session.add(case)
        db.session.commit()
        cid = case.id
        rec = UploadedFile(case_id=cid, filename='vegzes.pdf', uploader='doc', category='végzés')
        db.session.add(rec)
        db.session.commit()

    with client:
        login(client, 'doc', 'pw')
        resp = client.get(f'/ugyeim/{cid}/elvegzem')
        html = resp.get_data(as_text=True)
        assert 'Meg kell tekintenie a végzést a szerkesztés engedélyezéséhez' in html

        t1 = datetime(2025, 1, 1, 12, 0, tzinfo=BUDAPEST_TZ)
        monkeypatch.setattr('app.routes.now_local', lambda: t1)
        r2 = client.get(f'/cases/{cid}/mark_tox_viewed')
        assert r2.status_code == 204

        r3 = client.get(f'/ugyeim/{cid}/elvegzem')
        html2 = r3.get_data(as_text=True)
        assert 'Toxikológiai vizsgálatokat tartalmazó végzést megtekintettem' in html2

    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.tox_viewed_by_expert is True
        assert case.tox_viewed_at == t1.replace(tzinfo=None)
        log = ChangeLog.query.filter_by(case_id=cid, new_value='Toxi végzés megtekintve').first()
        assert log is not None