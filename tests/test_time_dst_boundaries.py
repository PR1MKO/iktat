from datetime import datetime, timezone

from app.utils.time_utils import fmt_budapest, to_budapest


def test_spring_forward_gap():
    before = datetime(2025, 3, 30, 0, 30, tzinfo=timezone.utc)
    after = datetime(2025, 3, 30, 1, 30, tzinfo=timezone.utc)
    assert fmt_budapest(before) == "2025/03/30 01:30"
    assert fmt_budapest(after) == "2025/03/30 03:30"
    assert to_budapest(before).tzname() == "CET"
    assert to_budapest(after).tzname() == "CEST"


def test_fall_back_overlap():
    before = datetime(2025, 10, 26, 0, 30, tzinfo=timezone.utc)
    after = datetime(2025, 10, 26, 1, 30, tzinfo=timezone.utc)
    assert fmt_budapest(before) == "2025/10/26 02:30"
    assert fmt_budapest(after) == "2025/10/26 02:30"
    assert to_budapest(before).tzname() == "CEST"
    assert to_budapest(after).tzname() == "CET"
