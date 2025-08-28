import re
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta

from app.utils.dates import compute_deadline_flags
from app.utils.time_utils import now_local


def test_no_datetime_in_templates():
    banned = [r"\.\s*date\(", r"\.strftime\(", r"\.isoformat\(", r"\| *localtime", r"\| *local_dt", r"\| *datetimeformat"]
    for tpl in Path('app/templates').rglob('*.html'):
        text = tpl.read_text()
        for pat in banned:
            assert re.search(pat, text) is None, f"{tpl} contains {pat}"


def test_compute_deadline_flags_boundaries():
    now = now_local()
    past = compute_deadline_flags(now - timedelta(days=1))
    today = compute_deadline_flags(now)
    future = compute_deadline_flags(now + timedelta(days=3))
    assert past["is_expired"] and not past["is_today"]
    assert today["is_today"] and not today["is_expired"]
    assert future["is_warning"] and future["days_left"] == 3


def test_sample_templates_render(app):
    app.jinja_env.globals['csrf_token'] = lambda: ''
    app.jinja_env.globals['current_user'] = SimpleNamespace(is_authenticated=False, role='')
    with app.test_request_context():
        case = SimpleNamespace(
            id=1,
            case_number='C1',
            deceased_name='D',
            status='open',
            registration_time_str='2024.01.01 10:00',
            deadline_str='2024.01.10 10:00',
            updated_at_iso='2024-01-02T00:00:00',
            uploaded_file_records=[SimpleNamespace(filename='f.txt', category='cat', upload_time_str='2024.01.02 11:00', uploader='u')],
            notes='',
        )
        changelog_entries = [SimpleNamespace(timestamp_str='2024.01.03 12:00', edited_by='u', new_value='v')]
        render = app.jinja_env.get_template('assign_pathologist.html').render(
            case=case,
            szakerto_users=[],
            szakerto_choices=[],
            szakerto_choices_2=[],
            changelog_entries=changelog_entries,
            uploads=case.uploaded_file_records,
            caps={}
        )
        assert 'form_version" value="2024-01-02T00:00:00"' in render

        users = [SimpleNamespace(id=1, username='u', screen_name='', full_name='', role='', last_login_str='')]
        render2 = app.jinja_env.get_template('admin_users.html').render(users=users)
        assert 'u' in render2