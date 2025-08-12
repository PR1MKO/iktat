# app/investigations/utils.py
import os
import re
import logging
from sqlalchemy import func
from app.utils.time_utils import now_local
from .models import Investigation

log = logging.getLogger(__name__)

_DRIVE_ONLY_RE = re.compile(r"^[A-Za-z]:$")
_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:[\\/]*$")  # C:, C:\, V:\, etc.

def resolve_upload_root(app):
    """Resolve a SAFE investigations upload root and log every decision."""
    requested = (app.config.get("INVESTIGATION_UPLOAD_FOLDER") or "").strip()
    instance_root = os.path.join(app.instance_path, "uploads_investigations")

    # Normalize requested path (if any)
    chosen = os.path.normpath(requested) if requested else instance_root

    # Guardrails: never allow bare drive or drive root
    if not chosen or _DRIVE_ONLY_RE.match(chosen) or _DRIVE_ROOT_RE.match(chosen):
        log.warning(
            "INV resolve_upload_root: rejecting invalid base '%s'; falling back to instance '%s'",
            requested or "<empty>", instance_root
        )
        chosen = instance_root

    # Final sanity: splitdrive check
    drive, tail = os.path.splitdrive(chosen)
    if drive and (tail in ("", "\\", "/")):
        log.warning(
            "INV resolve_upload_root: drive-root detected after norm '%s'; falling back to instance '%s'",
            chosen, instance_root
        )
        chosen = instance_root

    os.makedirs(chosen, exist_ok=True)

    log.info(
        "INV resolve_upload_root: requested='%s' -> chosen='%s' (instance_path='%s')",
        requested or "<empty>", chosen, app.instance_path
    )
    return chosen

def ensure_investigation_folder(app, case_number: str) -> str:
    base = resolve_upload_root(app)
    folder = os.path.join(base, case_number)
    # Extra guard: prevent creating folders directly under a drive root
    drive, tail = os.path.splitdrive(base)
    assert not (drive and tail in ("", "\\", "/")), f"Unsafe base resolved: {base}"
    os.makedirs(folder, exist_ok=True)
    log.info("INV ensure_investigation_folder: folder='%s'", folder)
    return folder

def generate_case_number(session) -> str:
    """
    Format: V-{####}-{YYYY}  (folder name & case_number)
    ####: 1-based, zero-padded to 4, unique per year.
    """
    year = now_local().year
    # Pull max existing like V-xxxx-YYYY
    max_cn = (
        session.query(func.max(Investigation.case_number))
        .filter(Investigation.case_number.like(f"V-%-{year}"))
        .scalar()
    )
    current_seq = 0
    if max_cn:
        try:
            current_seq = int(max_cn.split("-")[1])
        except Exception:
            current_seq = 0
    next_seq = current_seq + 1
    return f"V-{next_seq:04d}-{year}"
