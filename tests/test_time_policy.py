from datetime import timezone

from flask import render_template

from app.models import Case, IdempotencyToken, db
from app.utils.dates import attach_case_dates
from app.utils.time_utils import HUMAN_TIME_FMT, fmt_budapest, now_utc


def test_now_utc_awareness():
    dt = now_utc()
    assert dt.tzinfo == timezone.utc
    assert HUMAN_TIME_FMT == "%Y/%m/%d %H:%M"


def test_idempotency_token_created_at(app):
    with app.app_context():
        tok = IdempotencyToken(key="k", route="/r")
        db.session.add(tok)
        db.session.commit()
        assert tok.created_at.tzinfo == timezone.utc


def test_template_receives_preformatted_strings(app):
    with app.app_context():
        case = Case(case_number="C1", registration_time=now_utc(), deadline=now_utc())
        db.session.add(case)
        db.session.commit()
        attach_case_dates(case)
        with app.test_request_context():
            html = render_template(
                "elvegzem_base.html",
                case=case,
                changelog_entries=[],
                csrf_token=lambda: "",
            )
        assert case.registration_time_str in html
