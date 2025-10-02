from __future__ import annotations

import csv
import json
from datetime import timedelta

from app import db
from app.investigations.models import InvestigationChangeLog
from app.models import Case, ChangeLog
from app.utils.time_utils import fmt_budapest, now_utc
from tests.helpers import create_investigation, create_user, login


def _seed_changelog_data(app):
    with app.app_context():
        admin = create_user("admin", "secret", "admin")
        viewer = create_user("viewer", "secret", "leíró")

        case = Case(case_number="CASE-001")
        db.session.add(case)
        db.session.commit()

        base = now_utc()
        recent_case = ChangeLog(
            case_id=case.id,
            field_name="status",
            old_value="new",
            new_value="in_progress",
            edited_by="alice",
            timestamp=base - timedelta(minutes=30),
        )
        older_case = ChangeLog(
            case_id=case.id,
            field_name="notes",
            old_value="",
            new_value="Updated",
            edited_by="bob",
            timestamp=base - timedelta(days=2),
        )
        db.session.add_all([recent_case, older_case])

        investigation = create_investigation()
        inv_log = InvestigationChangeLog(
            investigation_id=investigation.id,
            field_name="assigned_expert_id",
            old_value="0",
            new_value="42",
            edited_by=viewer.id,
            timestamp=base - timedelta(minutes=5),
        )
        db.session.add(inv_log)
        db.session.commit()

        return {
            "admin": admin,
            "viewer": viewer,
            "case_id": case.id,
            "investigation_id": investigation.id,
            "recent_case_time": fmt_budapest(
                recent_case.timestamp, "%Y-%m-%d %H:%M:%S"
            ),
            "older_case_time": fmt_budapest(older_case.timestamp, "%Y-%m-%d %H:%M:%S"),
            "investigation_time": fmt_budapest(inv_log.timestamp, "%Y-%m-%d %H:%M:%S"),
        }


def test_admin_changelog_requires_admin(client, app):
    data = _seed_changelog_data(app)

    resp = client.get("/admin/changelog")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    with client:
        login(client, data["viewer"].username, "secret")
        resp = client.get("/admin/changelog")
        assert resp.status_code == 403

    with client:
        login(client, data["admin"].username, "secret")
        resp = client.get("/admin/changelog")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Változásnapló" in body
        assert "Ügy #" in body


def test_admin_changelog_renders_entries_from_both_binds(client, app):
    data = _seed_changelog_data(app)

    with client:
        login(client, data["admin"].username, "secret")
        resp = client.get("/admin/changelog")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert f"Ügy #{data['case_id']}" in body
        assert f"Vizsgálat #{data['investigation_id']}" in body
        assert data["recent_case_time"] in body
        assert data["investigation_time"] in body


def test_admin_changelog_filters_and_pagination(client, app):
    data = _seed_changelog_data(app)

    with client:
        login(client, data["admin"].username, "secret")

        resp = client.get("/admin/changelog", query_string={"per_page": 1})
        html = resp.get_data(as_text=True)
        assert f"Vizsgálat #{data['investigation_id']}" in html
        assert f"Ügy #{data['case_id']}" not in html

        resp = client.get(
            "/admin/changelog",
            query_string={"per_page": 1, "page": 2},
        )
        html = resp.get_data(as_text=True)
        assert f"Ügy #{data['case_id']}" in html
        assert data["investigation_time"] not in html

        resp = client.get(
            "/admin/changelog",
            query_string={
                "subject_type": "investigation",
                "subject_id": data["investigation_id"],
            },
        )
        html = resp.get_data(as_text=True)
        assert f"Vizsgálat #{data['investigation_id']}" in html
        assert f"Ügy #{data['case_id']}" not in html

        resp = client.get(
            "/admin/changelog",
            query_string={
                "date_start": data["recent_case_time"][:10],
                "date_end": data["recent_case_time"][:10],
            },
        )
        html = resp.get_data(as_text=True)
        assert data["recent_case_time"] in html
        assert data["older_case_time"] not in html

        resp = client.get(
            "/admin/changelog",
            query_string={"actor": data["viewer"].username},
        )
        html = resp.get_data(as_text=True)
        assert f"Vizsgálat #{data['investigation_id']}" in html
        assert f"Ügy #{data['case_id']}" not in html


def test_admin_changelog_csv_export(client, app):
    data = _seed_changelog_data(app)

    with client:
        login(client, data["admin"].username, "secret")
        resp = client.get("/admin/changelog.csv")
        assert resp.status_code == 200
        text = resp.get_data(as_text=True)
        assert text.startswith("\ufeff")
        rows = list(csv.reader(text.lstrip("\ufeff").splitlines(), delimiter=";"))
        assert rows[0] == [
            "Típus",
            "Időpont (Budapest)",
            "Szerkesztő",
            "Tárgy",
            "Mező",
            "Régi érték",
            "Új érték",
        ]
        assert any(data["investigation_time"] in "".join(row) for row in rows[1:])


def test_admin_changelog_jsonl_export(client, app):
    data = _seed_changelog_data(app)

    with client:
        login(client, data["admin"].username, "secret")
        resp = client.get("/admin/changelog.jsonl")
        assert resp.status_code == 200
        lines = [ln for ln in resp.get_data(as_text=True).splitlines() if ln.strip()]
        payloads = [json.loads(line) for line in lines]
        assert any(item["type"] == "investigation" for item in payloads)
        assert all(
            item["timestamp_local"].endswith(("+01:00", "+02:00")) for item in payloads
        )
