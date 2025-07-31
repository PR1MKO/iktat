# utils/case_helpers.py
from app.models import ChangeLog
from .time_utils import BUDAPEST_TZ
import pytz

def build_case_context(case):
    grouped_orders = []
    if case.tox_orders:
        order_map = {}
        for line in case.tox_orders.strip().split('\n'):
            try:
                test_name, rest = line.split(': ', 1)
                ts = rest.split(' – ', 1)[0]
                order_map.setdefault(ts, []).append(test_name)
            except ValueError:
                continue
        grouped_orders = sorted(order_map.items())[-5:]

    changelog_entries = (
        ChangeLog.query
        .filter_by(case_id=case.id)
        .order_by(ChangeLog.timestamp.desc())
        .limit(5)
        .all()
    )

    formatted_ts = ''
    if case.certificate_generated_at:
        ts = case.certificate_generated_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=pytz.UTC)
        formatted_ts = ts.astimezone(BUDAPEST_TZ).strftime('%Y.%m.%d %H:%M')

    return {
        'grouped_orders': grouped_orders,
        'changelog_entries': changelog_entries,
        'formatted_certificate_timestamp': formatted_ts,
        'show_certificate_message': bool(case.certificate_generated)
    }

