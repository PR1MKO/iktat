import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import IdempotencyToken


def claim_idempotency(
    key: str,
    *,
    route: str,
    user_id: Optional[int],
    case_id: Optional[int],
    ttl_seconds: int = 300,
) -> bool:
    ttl = current_app.config.get("IDEMPOTENCY_TTL_SECONDS", ttl_seconds)
    now = datetime.now(timezone.utc)
    expiry = now - timedelta(seconds=ttl)
    db.session.query(IdempotencyToken).filter(IdempotencyToken.created_at < expiry).delete()
    token = IdempotencyToken(
        key=key,
        route=route,
        user_id=user_id,
        case_id=case_id,
        created_at=now,
    )
    try:
        db.session.add(token)
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


def make_default_key(request, extra: str = "") -> str:
    user_id = getattr(current_user, "id", None)
    case_id = None
    if request.view_args:
        case_id = request.view_args.get("case_id")
    endpoint = request.endpoint or request.path
    body = {}
    if request.method in ("POST", "PUT", "PATCH"):
        if request.is_json:
            body = request.get_json(silent=True) or {}
        else:
            body = request.form.to_dict(flat=True)
    serialized = json.dumps(body, sort_keys=True, separators=(",", ":"))
    raw = f"{endpoint}|{user_id}|{case_id}|{serialized}|{extra}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()