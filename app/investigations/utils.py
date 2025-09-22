# app/investigations/utils.py
import shutil
from pathlib import Path

from flask import current_app
from sqlalchemy import func

from app.paths import ensure_investigation_folder as ensure_invest_path
from app.paths import investigation_root as invest_root_path
from app.utils.time_utils import now_utc, to_budapest

from .models import Investigation


def resolve_investigation_upload_root(app) -> str:
    return str(invest_root_path())


def resolve_upload_root(app) -> str:
    return str(invest_root_path())


def ensure_investigation_folder(app, case_number: str) -> str:
    return str(ensure_invest_path(case_number))


def init_investigation_upload_dirs(case_or_inv) -> str:
    """Seed per-investigation upload scaffold.

    Accepts a case number string or an Investigation instance. Ensures the
    investigation folder exists, creates a ``DO-NOT-EDIT`` subdirectory and
    copies template files from ``instance/docs/vizsgalat`` into it. Existing
    files are left untouched so repeated calls are safe.
    """

    if isinstance(case_or_inv, Investigation):
        case_number = case_or_inv.case_number
    else:
        case_number = str(case_or_inv)

    inv_root = ensure_invest_path(case_number)
    target = inv_root / "DO-NOT-EDIT"
    target.mkdir(exist_ok=True)

    src_root = Path(current_app.instance_path) / "docs" / "vizsgalat"
    if not src_root.exists():
        current_app.logger.warning("Investigation template dir missing: %s", src_root)
        return str(target)

    for item in src_root.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            if not dest.exists():
                shutil.copy2(item, dest)

    return str(target)


def generate_case_number(session) -> str:
    """
    Investigation case number format (legacy, for tests): V:####/YYYY
    - #### is 1-based, zero-padded to 4, unique per calendar year.
    """
    year = to_budapest(now_utc()).year

    # Seed: count existing in this year (registration_time), then ensure uniqueness by case_number.
    count_for_year = (
        session.query(func.count(Investigation.id))
        .filter(func.strftime("%Y", Investigation.registration_time) == str(year))
        .scalar()
        or 0
    )
    seq = count_for_year + 1

    while True:
        candidate = f"V:{seq:04d}/{year}"
        exists = (
            session.query(Investigation.id)
            .filter(Investigation.case_number == candidate)
            .first()
        )
        if not exists:
            return candidate
        seq += 1


def user_display_name(u):
    return (u.full_name or u.screen_name or u.username) if u else "—"


def display_name(user) -> str:
    """Return a user's preferred display name with sane fallbacks."""
    if not user:
        return "–"
    return getattr(user, "screen_name", None) or getattr(user, "username", None) or "–"
