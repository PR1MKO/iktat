# utils/case_helpers.py
from flask import flash, redirect, url_for

from app.models import ChangeLog

from .case_status import is_final_status
from .dates import safe_fmt
from .time_utils import fmt_budapest


def build_case_context(case):
    grouped_orders = []
    if case.tox_orders:
        order_map = {}
        for line in case.tox_orders.strip().split("\n"):
            try:
                test_name, rest = line.split(": ", 1)
                ts = rest.split(" – ", 1)[0]
                order_map.setdefault(ts, []).append(test_name)
            except ValueError:
                continue
        grouped_orders = sorted(order_map.items())[-5:]

    changelog_entries = (
        ChangeLog.query.filter_by(case_id=case.id)
        .order_by(ChangeLog.timestamp.desc())
        .limit(5)
        .all()
    )
    for entry in changelog_entries:
        entry.timestamp_str = safe_fmt(getattr(entry, "timestamp", None))

    formatted_ts = ""
    if case.certificate_generated_at:
        formatted_ts = fmt_budapest(case.certificate_generated_at)

    uploads = list(getattr(case, "uploaded_file_records", []) or [])
    for rec in uploads:
        rec.upload_time_str = safe_fmt(getattr(rec, "upload_time", None))

    return {
        "grouped_orders": grouped_orders,
        "changelog_entries": changelog_entries,
        "formatted_certificate_timestamp": formatted_ts,
        "show_certificate_message": bool(case.certificate_generated),
        "uploaded_file_records": uploads,
    }


def ensure_unlocked_or_redirect(
    case, redirect_endpoint="auth.case_detail", **endpoint_kwargs
):
    if is_final_status(case.status):
        flash("Az ügy lezárva; módosítás nem engedélyezett.", "warning")
        return redirect(url_for(redirect_endpoint, **endpoint_kwargs))
    return None
