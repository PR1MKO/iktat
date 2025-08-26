import pytest
from flask import render_template, render_template_string, url_for
from flask_login import AnonymousUserMixin

from app import create_app, login_manager


class Guest(AnonymousUserMixin):
    role = ''
    screen_name = ''
    username = ''


@pytest.fixture(scope="module")
def app():
    app = create_app({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'example.test',
    })
    login_manager.anonymous_user = Guest
    return app


case_stub = {
    'id': 1,
    'case_number': 'CASE-1',
    'name': 'Test',
    'status': 'nyitott',
    'deadline': None,
    'notes': [],
    'tox_orders': [],
    'files': [],
    'formatted_deadline': '',
    'case_type': '',
    'institution_name': '',
    'deceased_name': '',
}


templates = [
    ('base.html', 'auth.login', False, {}),
    (
        'list_cases.html',
        'auth.list_cases',
        False,
        {
            'cases': [],
            'users_map': {},
            'sort_by': '',
            'sort_order': '',
            'query_params': {},
            'search_query': '',
            'case_type_filter': '',
            'status_filter': '',
        },
    ),
    (
        'edit_case.html',
        'auth.edit_case',
        True,
        {'case': case_stub, 'szakerto_users': [], 'leiro_users': []},
    ),
    (
        'case_detail.html',
        'auth.case_detail',
        True,
        {'case': case_stub, 'caps': {'can_upload_case': False}, 'changelog_entries': []},
    ),
    (
        'case_documents.html',
        'auth.case_documents',
        True,
        {'case': case_stub},
    ),
    ('login.html', 'auth.login', False, {}),
]


@pytest.mark.parametrize("tmpl, endpoint, needs_id, ctx", templates)
def test_render_templates(app, tmpl, endpoint, needs_id, ctx):
    with app.app_context():
        path = url_for(endpoint, case_id=1) if needs_id else url_for(endpoint)
    with app.test_request_context(path):
        render_template(tmpl, **ctx)


def test_macros(app):
    with app.test_request_context('/'):
        render_template_string(
            "{% import 'includes/case_macros.html' as cm %}"
            "{{ cm.cases_filter_form() }}"
            "{{ cm.cases_table([]) }}"
        )


def test_url_map_build(app):
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if rule.endpoint == 'static':
                continue
            if rule.arguments - {'case_id'}:
                continue
            kwargs = {'case_id': 1} if 'case_id' in rule.arguments else {}
            url_for(rule.endpoint, **kwargs)
