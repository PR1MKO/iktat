import io
import os
from datetime import datetime, timedelta

import pytest
from app.models import User, Case, UploadedFile, db
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
            'registration_time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),
            'beerk_modja': 'Email',
        }
        resp = client.post('/cases/new', data=data, follow_redirects=False)
        assert resp.status_code == 302
        assert '/cases/' in resp.headers['Location']
    with app.app_context():
        assert Case.query.count() == initial + 1
        case = Case.query.first()
        assert case.case_number
        assert case.status == 'beérkezett'
        assert case.deadline.date() == (case.registration_time + timedelta(days=30)).date()


def test_case_creation_missing_required(client, app):
    with app.app_context():
        create_user()
        initial = Case.query.count()
    with client:
        login(client, 'admin', 'secret')
        resp = client.post('/cases/new', data={}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'T\xc3\xadpus, Regisztr\xc3\xa1lva, Be\xc3\xa9rkez\xc3\xa9s m\xc3\xb3dja kit\xc3\xb6lt\xc3\xa9se k\xc3\xb6telez\xc5\x91' in resp.data
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
        data = {'file': (io.BytesIO(b'pdfdata'), 'report.pdf')}
        resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data')
        assert resp.status_code == 302
    upload_path = os.path.join(app.root_path, 'uploads', str(case_id), 'report.pdf')
    assert os.path.exists(upload_path)
    with app.app_context():
        rec = UploadedFile.query.filter_by(case_id=case_id, filename='report.pdf').first()
        assert rec is not None


def test_upload_requires_auth(client, app):
    with app.app_context():
        create_user()
        case = Case(case_number='TEST2')
        db.session.add(case)
        db.session.commit()
        case_id = case.id
    data = {'file': (io.BytesIO(b'x'), 'file.pdf')}
    resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']
    upload_path = os.path.join(app.root_path, 'uploads', str(case_id), 'file.pdf')
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
        data = {'file': (io.BytesIO(b'abc'), 'closed.pdf')}
        resp = client.post(f'/cases/{case_id}/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
        assert resp.status_code == 302
        assert '/cases/' in resp.headers['Location']
    upload_path = os.path.join(app.root_path, 'uploads', str(case_id), 'closed.pdf')
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
            data={'file': (large_data, 'big.pdf')},
            content_type='multipart/form-data'
        )
        assert resp.status_code == 413
    upload_path = os.path.join(app.root_path, 'uploads', str(case_id), 'big.pdf')
    assert not os.path.exists(upload_path)
    with app.app_context():
        assert UploadedFile.query.filter_by(case_id=case_id).count() == 0
        
