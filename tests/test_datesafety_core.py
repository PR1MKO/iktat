from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.utils.dates import attach_case_dates
from app.utils.time_utils import now_local


@pytest.mark.date
def test_deadline_variants_render(app):
    with app.app_context():
        now = now_local()
        cases = []
        deltas = [None, -1, 0, 1]
        for idx, d in enumerate(deltas):
            case = SimpleNamespace(
                id=idx + 1,
                case_number=f"C{idx}",
                deceased_name="D",
                case_type="t",
                status="open",
                registration_time=now,
                deadline=None if d is None else now + timedelta(days=d),
                uploaded_file_records=[],
            )
            attach_case_dates(case)
            case.formatted_deadline = case.deadline_str
            cases.append(case)
        app.jinja_env.globals["csrf_token"] = lambda: ""
        app.jinja_env.globals["current_user"] = SimpleNamespace(is_authenticated=False, role="")
        with app.test_request_context():
            render = app.jinja_env.get_template("closed_cases.html").render(cases=cases)
        assert cases[1].deadline_flags["is_expired"]
        assert cases[2].deadline_flags["is_today"]
        assert cases[3].deadline_flags["is_warning"]
        assert cases[0].deadline_flags["days_left"] is None
        for c in cases[1:]:
            assert c.formatted_deadline in render