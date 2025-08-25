import io
import pytest
from app.models import Case, db, UploadedFile, AuditLog
from app.utils.time_utils import now_local
from tests.helpers import create_user, login
from docx import Document


def _create_case(status='beérkezett', **kw):
    case = Case(
        case_number='C' + kw.get('suffix', '1'),
        registration_time=now_local(),
        status=status,
        **{k: v for k, v in kw.items() if k != 'suffix'}
    )
    db.session.add(case)
    db.session.commit()
    return case.id


def test_locked_case_blocks_edit_redirects(client, app):
    with app.app_context():
        create_user('iroda', 'pw', 'iroda')
        case_id = _create_case(status='lezárt')
    login(client, 'iroda', 'pw')
    resp = client.post(f'/cases/{case_id}/edit', data={'deceased_name':'X'}, follow_redirects=True)
    assert 'Az ügy lezárva' in resp.get_data(as_text=True)
    assert any(r.status_code == 302 for r in resp.history)


def test_locked_case_blocks_assign_describer_json(client, app):
    with app.app_context():
        create_user('szak', 'pw', 'szakértő')
        case_id = _create_case(status='lezárt', expert_1='szak')
    login(client, 'szak', 'pw')
    resp = client.post(
        f'/ugyeim/{case_id}/assign_describer',
        json={'describer':'d'},
    )
    assert resp.status_code == 409
    assert resp.get_json()['error'] == 'Az ügy lezárva'
    with app.app_context():
        refreshed = db.session.get(Case, case_id)
        assert refreshed.describer is None


def test_step_order_enforced_describer_requires_status(client, app):
    with app.app_context():
        create_user('leiro', 'pw', 'leíró')
        case_id = _create_case(status='beérkezett', describer='leiro')
    login(client, 'leiro', 'pw')
    resp = client.get(f'/leiro/ugyeim/{case_id}/elvegzem', follow_redirects=True)
    assert 'Az ügy nincs a leírónál.' in resp.get_data(as_text=True)


def test_step_order_enforced_tox_view_requires_order(client, app):
    with app.app_context():
        create_user('szak', 'pw', 'szakértő')
        case_id = _create_case(status='beérkezett', expert_1='szak', tox_ordered=False)
    login(client, 'szak', 'pw')
    resp = client.get(f'/cases/{case_id}/mark_tox_viewed', follow_redirects=True)
    assert 'Nincs toxikológiai vizsgálat elrendelve.' in resp.get_data(as_text=True)


def test_prg_login_failure_redirects_with_flash(client):
    resp = client.post('/login', data={'username':'x','password':'y'}, follow_redirects=True)
    assert 'Invalid username or password.' in resp.get_data(as_text=True)
    assert any(r.status_code == 302 for r in resp.history)


def test_idempotency_tox_doc_double_post_ignored(client, app, monkeypatch, tmp_path):
    with app.app_context():
        create_user('admin', 'pw', 'admin')
        case_id = _create_case(status='beérkezett')
        monkeypatch.setattr('app.views.auth.case_root', lambda: tmp_path)
        tpl_dir = tmp_path / 'autofill-word-do-not-edit'
        tpl_dir.mkdir(parents=True)
        doc = Document()
        doc.add_paragraph('{{case.case_number}}')
        doc.save(tpl_dir / 'Toxikológiai-kirendelő.docx')
    login(client, 'admin', 'pw')
    form = {'alkohol_minta_count':'0','alkohol_minta_ara':'0'}
    resp1 = client.post(f'/cases/{case_id}/generate_tox_doc', data=form, follow_redirects=True)
    assert resp1.status_code == 200
    resp2 = client.post(f'/cases/{case_id}/generate_tox_doc', data=form, follow_redirects=True)
    assert 'Művelet már feldolgozva.' in resp2.get_data(as_text=True)
    with app.app_context():
        files = UploadedFile.query.filter_by(case_id=case_id, category='Toxikológiai kirendelő').all()
        assert len(files) == 1
        logs = AuditLog.query.filter_by(action='Toxikológiai kirendelő generálva').all()
        assert len(logs) == 1


def test_admin_delete_blocked_on_finalized_case(client, app):
    with app.app_context():
        create_user('admin', 'pw', 'admin')
        case_id = _create_case(status='lezárt')
    login(client, 'admin', 'pw')
    resp = client.post(f'/admin/cases/{case_id}/delete', follow_redirects=True)
    assert 'Az ügy lezárva' in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Case, case_id) is not None


def test_closed_cases_page_shows_lezart_only(client, app):
    with app.app_context():
        create_user('admin', 'pw', 'admin')
        c1_id = _create_case(status='lezárt', suffix='1')
        c2_id = _create_case(status='beérkezett', suffix='2')
    login(client, 'admin', 'pw')
    resp = client.get('/cases/closed')
    text = resp.get_data(as_text=True)
    assert 'C1' in text
    assert 'C2' not in text