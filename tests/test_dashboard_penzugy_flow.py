import re
from datetime import timedelta

from app.models import Case, db
from app.utils.time_utils import now_local
from tests.helpers import create_user, login


def test_penzugy_redirects_to_dedicated_dashboard(client, app):
    with app.app_context():
        create_user("fin", "pw", role="pénzügy")
    with client:
        login(client, "fin", "pw")
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/dashboard/penzugy")


def test_penzugy_dashboard_matches_list_ordering(client, app):
    with app.app_context():
        create_user("fin", "pw", role="pénzügy")
        now = now_local()
        cases = [
            Case(case_number="B:1001/2024", deadline=now - timedelta(days=1)),
            Case(case_number="B:1002/2024", deadline=now + timedelta(days=1)),
            Case(case_number="B:1003/2024", deadline=now + timedelta(days=2)),
        ]
        db.session.add_all(cases)
        db.session.commit()
    with client:
        login(client, "fin", "pw")
        resp_dash = client.get("/dashboard/penzugy?sort_by=case_number&sort_order=desc")
        resp_list = client.get("/cases?sort_by=case_number&sort_order=desc")
        html_dash = resp_dash.get_data(as_text=True)
        html_list = resp_list.get_data(as_text=True)

    def extract(html):
        rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL)
        data = []
        for row in rows:
            m = re.search(r"/view_case[^>]*>([^<]+)</a>", row)
            if not m:
                continue
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            deadline_html = tds[6] if len(tds) > 6 else ""
            deadline = re.sub("<[^<]+?>", "", deadline_html).strip()
            data.append((m.group(1), deadline))
        return data

    cases_dash = extract(html_dash)
    cases_list = extract(html_list)
    assert cases_dash == cases_list
