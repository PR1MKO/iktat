"""Audit helpers for logging both actions and field-level diffs."""

from __future__ import annotations

import json
from typing import Iterable, List, Tuple

from flask import current_app, flash, has_request_context
from flask_login import current_user
from sqlalchemy.inspection import inspect

from app import db
from app.utils.time_utils import now_utc

TRUNCATE_AT = 500


def log_action(action: str, details: str | None = None) -> None:
    if not getattr(current_user, "is_authenticated", False):
        return  # Skip logging if no user is logged in

    from app.models import AuditLog

    log_entry = AuditLog(
        timestamp=now_utc(),
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action=action,
        details=details,
    )
    db.session.add(log_entry)
    try:
        db.session.commit()
    except Exception as e:  # pragma: no cover - extremely defensive
        db.session.rollback()
        current_app.logger.error(f"Database error: {e}")
        if has_request_context():
            flash("Valami hiba történt. Próbáld újra.", "danger")


def _stringify(value) -> str:
    """Return a truncated string representation for *value*."""

    if value is None:
        return "∅"
    try:
        if isinstance(value, (dict, list, tuple)):
            rendered = json.dumps(value, ensure_ascii=False, default=str)
        else:
            rendered = str(value)
    except Exception:  # pragma: no cover - extremely defensive
        rendered = repr(value)
    if len(rendered) > TRUNCATE_AT:
        return f"{rendered[:TRUNCATE_AT]} …[+{len(rendered) - TRUNCATE_AT}]"
    return rendered


def _is_pk(column) -> bool:
    try:
        return bool(getattr(column, "primary_key", False))
    except Exception:  # pragma: no cover - extremely defensive
        return False


def _iter_column_attr_names(instance) -> Iterable[str]:
    mapper = inspect(instance).mapper
    for col_attr in mapper.column_attrs:
        if any(_is_pk(col) for col in col_attr.columns):
            continue
        yield col_attr.key


def diff_for_update(instance) -> List[Tuple[str, str, str]]:
    """Return list of changed column names with old/new stringified values."""

    state = inspect(instance)
    changes: List[Tuple[str, str, str]] = []
    for name in _iter_column_attr_names(instance):
        attr = state.attrs.get(name)
        if attr is None:
            continue
        history = attr.history
        if not history.has_changes():
            continue
        old_val = None
        if history.deleted:
            old_val = history.deleted[0]
        elif history.unchanged:
            old_val = history.unchanged[0]
        new_val = history.added[0] if history.added else getattr(instance, name, None)
        changes.append((name, _stringify(old_val), _stringify(new_val)))
    return changes


def snapshot_for_insert(instance) -> List[Tuple[str, str, str]]:
    """Return snapshot of column values for newly inserted *instance*."""

    snapshot: List[Tuple[str, str, str]] = []
    for name in _iter_column_attr_names(instance):
        try:
            new_val = getattr(instance, name, None)
        except Exception:  # pragma: no cover - extremely defensive
            new_val = None
        snapshot.append((name, "∅", _stringify(new_val)))
    return snapshot
