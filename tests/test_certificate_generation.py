import os
import shutil
from app.models import Case, db
from tests.helpers import create_user, login


def create_case():
    case = Case(
        case_number='0001-2025',
        expert_1='doc',
        halalt_megallap_pathologus=True,
        boncolas_tortent=True,
        varhato_tovabbi_vizsgalat=False,
        kozvetlen_halalok='ok',
        kozvetlen_halalok_ido='1 nap',
        alapbetegseg_szovodmenyei='szov',
        alapbetegseg_szovodmenyei_ido='2 nap',
        alapbetegseg='beteg',
        alapbetegseg_ido='3 nap',
        kiserobetegsegek='egyeb'
    )
    db.session.add(case)
    db.session.commit()
    return case


def test_certificate_generation_success(client, app):
    with app.app_context():
        create_user('doc', 'pw', 'szakértő')
        case = create_case()
        cid = case.id
    upload_root = os.path.join(app.root_path, 'uploads')
    if os.path.exists(upload_root):
        shutil.rmtree(upload_root)
    form_data = {
        'halalt_megallap': 'pathologus',
        'boncolas_tortent': 'igen',
        'varhato_tovabbi_vizsgalat': 'nem',
        'kozvetlen_halalok': 'ok',
        'kozvetlen_halalok_ido': '1 nap',
        'alapbetegseg_szovodmenyei': 'szov',
        'alapbetegseg_szovodmenyei_ido': '2 nap',
        'alapbetegseg': 'beteg',
        'alapbetegseg_ido': '3 nap',
        'kiserobetegsegek': 'egyeb'
    }
    with client:
        login(client, 'doc', 'pw')
        resp = client.post(f'/ugyeim/{cid}/generate_certificate', data=form_data)
        assert resp.status_code == 302
        assert resp.headers['Location'].endswith(f'/ugyeim/{cid}/elvegzem')
    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.certificate_generated is True
        assert case.certificate_generated_at is not None
    path = os.path.join(app.root_path, 'uploads', case.case_number, f'halottvizsgalati_bizonyitvany-{case.case_number}.txt')
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]
    assert lines[0] == 'Ügy: 0001-2025'
    assert lines[2] == 'A halál okát megállapította: pathologus'
    assert lines[4] == 'Történt-e boncolás: igen'
    assert lines[5] == 'Ha igen, várhatók-e további vizsgálati eredmények: nem'
    assert lines[7] == 'Közvetlen halálok: ok'
    assert lines[8] == 'Esemény kezdete és halál között eltelt idő: 1 nap'
    assert lines[10] == 'Alapbetegség szövődményei: szov'
    assert lines[11] == 'Esemény kezdete és halál között eltelt idő: 2 nap'
    assert lines[13] == 'Alapbetegség: beteg'
    assert lines[14] == 'Esemény kezdete és halál között eltelt idő: 3 nap'
    assert lines[16] == 'Kísérő betegségek vagy állapotok: egyeb'
    assert lines[-1].startswith('Generálva: ')


def test_certificate_generation_optional_fields_blank(client, app):
    with app.app_context():
        create_user('doc', 'pw', 'szakértő')
        case = create_case()
        case.alapbetegseg = ''
        db.session.commit()
        cid = case.id
    upload_root = os.path.join(app.root_path, 'uploads')
    if os.path.exists(upload_root):
        shutil.rmtree(upload_root)
    form_data = {
        'halalt_megallap': 'pathologus',
        'boncolas_tortent': 'igen',
        'varhato_tovabbi_vizsgalat': 'nem',
        'kozvetlen_halalok': 'ok',
        'kozvetlen_halalok_ido': '1 nap',
        'alapbetegseg_szovodmenyei': '',
        'alapbetegseg_szovodmenyei_ido': '',
        'alapbetegseg': '',
        'alapbetegseg_ido': '',
        'kiserobetegsegek': ''
    }
    with client:
        login(client, 'doc', 'pw')
        resp = client.post(f'/ugyeim/{cid}/generate_certificate', data=form_data)
        assert resp.status_code == 302
        assert resp.headers['Location'].endswith(f'/ugyeim/{cid}/elvegzem')
    path = os.path.join(app.root_path, 'uploads', case.case_number, f'halottvizsgalati_bizonyitvany-{case.case_number}.txt')
    assert os.path.exists(path)
    with open(path, encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]
    assert lines[10] == 'Alapbetegség szövődményei: '
    assert lines[11] == 'Esemény kezdete és halál között eltelt idő: '
    assert lines[13] == 'Alapbetegség: '
    assert lines[14] == 'Esemény kezdete és halál között eltelt idő: '
    assert lines[16] == 'Kísérő betegségek vagy állapotok: '
    with app.app_context():
        case = db.session.get(Case, cid)
        assert case.certificate_generated is True
        assert case.certificate_generated_at is not None

