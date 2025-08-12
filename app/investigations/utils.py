```python
# app/investigations/utils.py
import os
import re
import logging
from sqlalchemy import func
from app.utils.time_utils import now_local
from .models import Investigation

log = logging.getLogger(__name__)

# Guard against invalid Windows roots like "V:" or "V:\"
_DRIVE_ONLY_RE = re.compile(r"^[A-Za-z]:$")
_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:[\\/]*$")  # C:, C:\, V:\, etc.

# Windows-illegal filename characters
_ILLEGAL_FS_CHARS = re.compile(r'[:*?"<>|]')


def _sanitize_folder_name(name: str) -> str:
    """
    Make a string safe for use as a Windows folder:
    - Replace illegal characters with '-'
    - Trim trailing spaces/dots
    - Collapse multiple dashes
    """
    clean = _ILLEGAL_FS_CHARS.sub("-", name).strip(" .")
    clean = re.sub(r"-{2,}", "-", clean)
    return clean


def resolve_upload_root(app):
    """
    Resolve a SAFE base folder for investigation uploads.
    Prefers app.config['INVESTIGATION_UPLOAD_FOLDER'] if valid; otherwise falls back to
    <instance_path>/uploads_investigations.
    """
    base = (app.config.get("INVESTIGATION_UPLOAD_FOLDER") or "").strip()

    # Reject empty, bare drive letters, or drive roots
    if (not base) or _DRIVE_ONLY_RE.match(base) or _DRIVE_ROOT_RE.match(base):
        base = os.path.join(app.instance_path, "uploads_investigations")

    # Normalize and re-check for accidental drive-root after normalization
    base = os.path.normpath(base)
    drive, tail = os.path.splitdrive(base)
    if drive and (tail in ("", "\\", "/")):
        base = os.path.join(app.instance_path, "uploads_investigations")

    os.makedirs(base, exist_ok=True)
    log.info("INV resolve_upload_root -> %s", base)
    return base


def ensure_investigation_folder(app, case_number: str) -> str:
    """
    Create (if needed) and return the per-investigation folder path.
    Folder name must match the case_number but sanitized for filesystem safety.
    """
    root = resolve_upload_root(app)
    safe_case = _sanitize_folder_name(case_number)
    folder = os.path.join(root, safe_case)

    # Final guard: avoid creating under a drive root
    drive, tail = os.path.splitdrive(root)
    assert not (drive and tail in ("", "\\", "/")), f"Unsafe base resolved: {root}"

    os.makedirs(folder, exist_ok=True)
    log.info("INV ensure_investigation_folder -> %s", folder)
    return folder


def generate_case_number(session) -> str:
    """
    Investigation case number format: V-{####}-{YYYY}
    - #### is 1-based, zero-padded to 4, unique per calendar year.
    - This replaces legacy format 'V:####/YYYY'. We still read legacy to avoid collisions.
    """
    year = now_local().year

    # New-format max for this year, relies on zero-padded #### so string max works.
    max_new = (
        session.query(func.max(Investigation.case_number))
        .filter(Investigation.case_number.like(f"V-%-{year}"))
        .scalar()
    )

    seq_new = 0
    if max_new:
        try:
            # "V-####-YYYY" -> take middle token
            seq_new = int(max_new.split("-")[1])
        except Exception:
            seq_new = 0

    # Legacy-format max for this year: "V:####/YYYY"
    max_legacy = (
        session.query(func.max(Investigation.case_number))
        .filter(Investigation.case_number.like(f"V:%/{year}"))
        .scalar()
    )

    seq_legacy = 0
    if max_legacy and max_legacy.startswith("V:"):
        try:
            # "V:####/YYYY" -> between ':' and '/'
            mid = max_legacy.split(":", 1)[1]
            seq_legacy = int(mid.split("/", 1)[0])
        except Exception:
            seq_legacy = 0

    next_seq = max(seq_new, seq_legacy) + 1
    return f"V-{next_seq:04d}-{year}"
```
