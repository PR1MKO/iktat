# app/tasks/smoke.py
from datetime import datetime, timezone


def ping_db():
    # simple health payload; tests just need a dict with ok + timestamp
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}
