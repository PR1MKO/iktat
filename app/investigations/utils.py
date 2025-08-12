import os
import re

from sqlalchemy.exc import IntegrityError
from app.utils.time_utils import now_local


def generate_case_number(db_session) -> str:
    """Generate unique case number V:0001/YYYY for investigations."""
    from app.investigations.models import Investigation

    year = now_local().year
    pattern = f"V:%/{year}"
    while True:
        last = (
            db_session.query(Investigation.case_number)
            .filter(Investigation.case_number.like(pattern))
            .order_by(Investigation.case_number.desc())
            .first()
        )
        last_num = int(last[0][2:6]) if last else 0
        case_number = f"V:{last_num + 1:04d}/{year}"
        try:
            exists = (
                db_session.query(Investigation.id)
                .filter_by(case_number=case_number)
                .first()
            )
            if exists is None:
                return case_number
            raise IntegrityError(None, None, None)
        except IntegrityError:
            db_session.rollback()
            continue


def resolve_upload_root(app):
    """Resolve investigation upload root.

    - Prefer app.config['INVESTIGATION_UPLOAD_FOLDER']
    - If it's a bare drive like 'V:', turn into 'V:\\'
    - If it's missing/unusable, fallback to instance/uploads_investigations
    """

    base = app.config.get("INVESTIGATION_UPLOAD_FOLDER")
    if not base:
        base = os.path.join(app.instance_path, "uploads_investigations")

    # Bare drive letter -> add slash
    if re.fullmatch(r"^[A-Za-z]:$", base):
        base = base + os.sep

    base = os.path.normpath(base)

    try:
        os.makedirs(base, exist_ok=True)
    except OSError:
        base = os.path.join(app.instance_path, "uploads_investigations")
        os.makedirs(base, exist_ok=True)

    if not os.path.isdir(base):
        base = os.path.join(app.instance_path, "uploads_investigations")
        os.makedirs(base, exist_ok=True)

    return base


def ensure_investigation_folder(app, case_number: str) -> str:
    """Ensure per-investigation folder exists (separate from Cases)."""
    root = resolve_upload_root(app)
    folder = os.path.join(root, case_number)
    os.makedirs(folder, exist_ok=True)
    return folder