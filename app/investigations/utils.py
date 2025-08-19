# app/investigations/utils.py
from sqlalchemy import func
from app.utils.time_utils import now_local
from .models import Investigation
from app.paths import (
    investigation_root as invest_root_path,
    ensure_investigation_folder as ensure_invest_path,
)

def resolve_investigation_upload_root(app) -> str:
    return str(invest_root_path())


def resolve_upload_root(app) -> str:
    return str(invest_root_path())

def ensure_investigation_folder(app, case_number: str) -> str:
    return str(ensure_invest_path(case_number))

def generate_case_number(session) -> str:
    """
    Investigation case number format (legacy, for tests): V:####/YYYY
    - #### is 1-based, zero-padded to 4, unique per calendar year.
    """
    year = now_local().year

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
    
