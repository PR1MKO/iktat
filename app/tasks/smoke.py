# app/tasks/smoke.py
from app.utils.time_utils import fmt_budapest, now_utc


def ping_db():
    """Simple health payload with human-friendly timestamp."""
    return {"ok": True, "ts": fmt_budapest(now_utc())}
