# app/investigations/utils.py
import os
import re
from sqlalchemy import func
from app.utils.time_utils import now_local
from .models import Investigation

_DRIVE_ONLY_RE = re.compile(r"^[A-Za-z]:$")

def resolve_upload_root(app):
    base = (app.config.get("INVESTIGATION_UPLOAD_FOLDER") or "").strip()
    if not base or _DRIVE_ONLY_RE.match(base):
        base = os.path.join(app.instance_path, "uploads_investigations")
    base = os.path.normpath(base)
    os.makedirs(base, exist_ok=True)
    return base

def ensure_investigation_folder(app, case_number: str) -> str:
    root = resolve_upload_root(app)
    folder = os.path.join(root, case_number)
    os.makedirs(folder, exist_ok=True)
    return folder

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
