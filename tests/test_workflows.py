import io
import os
from datetime import timedelta

from app.models import Case, UploadedFile, ChangeLog, db
from tests.helpers import create_user, login

def test_case_creation_success(client, app):
    with app.app_context():
        create_user()
        initial = Case.query.count()
    with client:
        login(client, 'admin', 'secret')
        data = {
            'case_type': 'test',
            'deceased_name': 'John Doe',
            'beerk_modja': 'Email',
            'temp_id': 'TEMP1',
        }
        resp = client.post('/cases/new', data=data, follow_redirects=False)
        assert resp.status_code == 302
        assert '/documents' in resp.headers['Location']
    with app.app_context():
        assert Case.query.count() == initial + 1
        case = Case.query.first()
        assert case.case_number
        assert case.status == 'beérkezett'
        assert case.deadline.date() == (case.registration_time + timedelta(days=30)).date()
 
 
def test_changelog_created_on_case_creation(client, app):
    with app.app_context():
        create_user()
    with client:
        login(client, 'admin', 'secret')
        data = {
            'case_type': 'test',
            'beerk_modja': 'Email',
            'temp_id': 'TEMP2',
        }
        resp = client.post('/cases/new', data=data, follow_redirects=False)
        assert resp.status_code == 302
        assert '/documents' in resp.headers['Location']
    with app.app_context():
        case = Case.query.order_by(Case.id.desc()).first()
        log = ChangeLog.query.filter_by(case_id=case.id, field_name='system').first()
        assert log is not None
        assert log.new_value == 'ügy érkeztetve'
        assert log.edited_by == 'admin'


def test_case_creation_missing_required(client, app):
    with app.app_context():
        create_user()
        initial = Case.query.count()
    with client:
        login(client, 'admin', 'secret')
        resp = client.post('/cases/new', data={}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'T\xc3\xadpus, Be\xc3\xa9rkez\xc3\xa9s m\xc3\xb3dja kit\xc3\xb6lt\xc3\xa9se k\xc3\xb6telez\xc5\x91.' in resp.data
    with app.app_context():
        assert Case.query.count() == initial


def test_get_new_case_form(client, app):
    with app.app_context():
        create_user()
    with client:
        login(client, 'admin', 'secret')
        resp = client.get('/cases/new')
        assert resp.status_code == 200
        assert b'name="external_id"' in resp.data
        assert b'name="temp_id"' in resp.data


def test_case_creation_requires_identifier(client, app):
    with app.app_context():
        create_user()
        initial = Case.query.count()
    with client:
        login(client, 'admin', 'secret')
        data = {
            'case_type': 'test',
            'beerk_modja': 'Email',
        }
        resp = client.post('/cases/new', data=data, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Legal\xc3\xa1bb az egyik azonos\xc3\xadt\xc3\xb3t meg kell adni' in resp.data
    with app.app_context():
        assert Case.query.count() == initial


def test_file_upload_success(client, app, tmp_path):
    with app.app_context():
        create_user()
        case = Case(case_number='TEST1')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    with client:
        login(client, 'admin', 'secret')
        data = {'file': (io.BytesIO(b'pdfdata'), 'report.pdf'), 'category': 'egyéb'}
        resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 302
    upload_path = os.path.join(app.root_path, 'uploads', case.case_number, 'report.pdf')
    assert os.path.exists(upload_path)
    with app.app_context():
        rec = UploadedFile.query.filter_by(case_id=case_id, filename='report.pdf').first()
        assert rec is not None

def test_upload_redirects_back_to_documents(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='DOCRED')
        db.session.add(case)
        db.session.commit()
        cid = case.id
    with client:
        login(client, 'admin', 'secret')
        data = {'file': (io.BytesIO(b'x'), 'file.pdf'), 'category': 'egyéb'}
        resp = client.post(
            f'/cases/{cid}/upload',
            data=data,
            content_type='multipart/form-data',
            headers={'Referer': f'http://localhost/cases/{cid}/documents'}
        )
        assert resp.status_code == 302
        assert resp.headers['Location'].endswith(f'/cases/{cid}/documents')

def test_upload_requires_auth(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='TEST2')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    data = {'file': (io.BytesIO(b'x'), 'file.pdf'), 'category': 'egyéb'}
    resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']
    upload_path = os.path.join(app.root_path, 'uploads', case.case_number, 'file.pdf')
    assert not os.path.exists(upload_path)


def test_upload_blocked_for_finalized_case(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='TEST3', status='lezárva')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    with client:
        login(client, 'admin', 'secret')
        data = {'file': (io.BytesIO(b'abc'), 'closed.pdf'), 'category': 'egyéb'}
        resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
        assert resp.status_code == 302
        assert '/cases/' in resp.headers['Location']
    upload_path = os.path.join(app.root_path, 'uploads', case.case_number, 'closed.pdf')
    assert not os.path.exists(upload_path)
    with app.app_context():
        assert UploadedFile.query.filter_by(case_id=case_id).count() == 0


def test_upload_large_file_blocked(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='TEST4')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    large_data = io.BytesIO(b'x' * (17 * 1024 * 1024))
    with client:
        login(client, 'admin', 'secret')
        resp = client.post(
            f'/cases/{case_id}/upload',
            data={'file': (large_data, 'big.pdf'), 'category': 'egyéb'},
            content_type='multipart/form-data'
        )
        assert resp.status_code == 413
    upload_path = os.path.join(app.root_path, 'uploads', case.case_number, 'big.pdf')
    assert not os.path.exists(upload_path)
    with app.app_context():
        assert UploadedFile.query.filter_by(case_id=case_id).count() == 0
        
def test_file_download_success(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='DL1')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
        upload_dir = os.path.join(app.root_path, 'uploads', case.case_number)
        os.makedirs(upload_dir, exist_ok=True)
        with open(os.path.join(upload_dir, 'file.txt'), 'wb') as f:
            f.write(b'data')
        db.session.add(
            UploadedFile(case_id=case_id, filename='file.txt', uploader='admin', category='egyéb')
        )
        db.session.commit()
    with client:
        login(client, 'admin', 'secret')
        resp = client.get(f'/cases/{case_id}/files/file.txt')
        assert resp.status_code == 200
        assert resp.data == b'data'


def test_file_download_not_found(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='DL2')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.get(f'/cases/{case_id}/files/missing.txt')
        assert resp.status_code == 404


def test_file_download_traversal_blocked(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='DL3')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    with client:
        login(client, 'admin', 'secret')
        resp = client.get(f'/cases/{case_id}/files/../secret.txt')
        assert resp.status_code == 403


def test_elvegzem_auto_assigns_default_describer(client, app):
    with app.app_context():
        leiro = create_user('leiro', 'pw', role='leíró')
        expert = create_user('doc', 'pw', role='szakértő')
        expert.default_leiro_id = leiro.id
        case = Case(case_number='AUTO1', expert_1='doc')
        db.session.add(case)
        db.session.commit()
        cid = case.id

    with client:
        login(client, 'doc', 'pw')
        resp = client.post(f'/ugyeim/{cid}/elvegzem', data={})
        assert resp.status_code == 302

    with app.app_context():
        updated = db.session.get(Case, cid)
        assert updated.describer == 'leiro'


def test_elvegzem_keeps_existing_describer(client, app):
    with app.app_context():
        leiro = create_user('leiro2', 'pw', role='leíró')
        expert = create_user('doc2', 'pw', role='szakértő')
        expert.default_leiro_id = leiro.id
        case = Case(case_number='AUTO2', expert_1='doc2', describer='other')
        db.session.add(case)
        db.session.commit()
        cid = case.id

    with client:
        login(client, 'doc2', 'pw')
        resp = client.post(f'/ugyeim/{cid}/elvegzem', data={})
        assert resp.status_code == 302

    with app.app_context():
        updated = db.session.get(Case, cid)
        assert updated.describer == 'other'    
        