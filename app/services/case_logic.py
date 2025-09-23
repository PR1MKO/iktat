"""Case-related read helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_

from app import db
from app.models import Case, User


def _normalized(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    trimmed = value.strip()
    return trimmed or None


def _resolve_user_by_identifier(identifier: Optional[str]) -> Optional[User]:
    ident = _normalized(identifier)
    if not ident:
        return None
    return User.query.filter(
        or_(User.screen_name == ident, User.username == ident)
    ).first()


def _user_display_label(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    for candidate in (user.screen_name, user.username):
        label = _normalized(candidate)
        if label:
            return label
    return None


def _resolve_default_leiro(expert_user: User) -> Optional[User]:
    user_id = getattr(expert_user, "default_leiro_id", None)
    if not user_id:
        return None
    return db.session.get(User, user_id)


def resolve_effective_describer(case: Case) -> Optional[str]:
    """Return the display label of the effective describer for a case."""
    explicit = _normalized(case.describer)
    if explicit:
        return explicit

    for expert_identifier in (case.expert_1, case.expert_2):
        expert_user = _resolve_user_by_identifier(expert_identifier)
        if not expert_user:
            continue
        fallback_user = _resolve_default_leiro(expert_user)
        label = _user_display_label(fallback_user)
        if label:
            return label

    return None
