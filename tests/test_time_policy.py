import pytest
from flask import render_template

from app.models import Case, IdempotencyToken, db
from app.utils.time_utils import BUDAPEST_TZ, now_local, to_local


def test_now_local_awareness():
    dt = now_local()
    assert to_local(dt).tzinfo.zone == BUDAPEST_TZ.zone


def test_idempotency_token_created_at(app):
    with app.app_context():
        tok = IdempotencyToken(key="k", route="/r")
        db.session.add(tok)
        db.session.commit()
        assert to_local(tok.created_at).tzinfo == BUDAPEST_TZ


def test_template_uses_local_dt(app, monkeypatch):
    with app.app_context():
        case = Case(
            case_number="C1", registration_time=now_local(), deadline=now_local()
        )
        db.session.add(case)
        db.session.commit()

        monkeypatch.setitem(
            app.jinja_env.filters, "local_dt", lambda v, fmt="%Y-%m-%d": "LOC"
        )
        with app.test_request_context():
            html = render_template(
                "elvegzem_base.html",
                case=case,
                changelog_entries=[],
                csrf_token=lambda: "",
            )
        assert "LOC" not in html


def test_columns_timezone_flag(app):
    with app.app_context():
        if db.engine.url.get_backend_name() == "sqlite":
            pytest.skip("SQLite does not store timezone metadata")
        insp = db.inspect(db.engine)
        case_cols = {c["name"]: c["type"] for c in insp.get_columns("case")}
        assert getattr(case_cols["certificate_generated_at"], "timezone", False)
