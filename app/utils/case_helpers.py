# utils/case_helpers.py
from app.models import ChangeLog

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

    return {
        'grouped_orders': grouped_orders,
        'changelog_entries': changelog_entries
    }
