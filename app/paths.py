import os, re
from flask import current_app

_DRIVE_ONLY_RE = re.compile(r"^[A-Za-z]:$")

def _norm(p: str) -> str:
    return os.path.normpath(p)

def _safe_root(config_key: str, default_subdir: str, legacy_keys: list[str]) -> str:
    app = current_app
    candidates = [
        (app.config.get(config_key) or "").strip(),
        *[(app.config.get(k) or "").strip() for k in legacy_keys],
    ]
    raw = next((c for c in candidates if c and not _DRIVE_ONLY_RE.match(c)), None)
    if not raw:
        raw = os.path.join(app.root_path, default_subdir)
    root = _norm(raw)
    os.makedirs(root, exist_ok=True)
    return root

# === CASE uploads (boncolások) ===
def case_root() -> str:
    # canonical default: <app_root>/uploads_boncolasok
    legacy = ["UPLOAD_FOLDER", "CASE_UPLOAD_FOLDER_LEGACY", "CASE_UPLOAD_DIR"]
    return _safe_root("CASE_UPLOAD_FOLDER", "uploads_boncolasok", legacy)
    
def _safe_case_segment(s: str) -> str:
    # Windows-safe normalization for folder segments
    return (s or "").replace(":", "-").replace("/", "-").strip(" .")

def file_safe_case_number(n: str) -> str:
    """Public: convert case_number to a Windows-safe filename segment."""
    return _safe_case_segment(n)

def case_folder_name(case_number: str) -> str:
    safe = _safe_case_segment(case_number)
    return safe if safe.startswith("B-") else f"B-{safe}"

def ensure_case_folder(case_number: str) -> str:
    folder = _norm(os.path.join(case_root(), case_folder_name(case_number)))
    os.makedirs(folder, exist_ok=True)
    return folder

# === INVESTIGATION uploads (vizsgálatok) ===
def investigation_root() -> str:
    # canonical default: EXACT absolute path requested by user
    default_path = r"C:\Users\kiss.istvan3\Desktop\folyamatok\IKTATAS2.0\forensic-case-tracker\app\uploads_vizsgalatok"
    app = current_app
    raw = (app.config.get("INVESTIGATION_UPLOAD_FOLDER") or "").strip()
    # If config is empty or only a drive letter, use the EXACT default absolute path.
    if not raw or _DRIVE_ONLY_RE.match(raw):
        raw = default_path
    root = _norm(raw)
    os.makedirs(root, exist_ok=True)
    return root

def ensure_investigation_folder(case_number: str) -> str:
    safe = case_number.replace(":", "-").replace("/", "-").strip(" .")
    folder = _norm(os.path.join(investigation_root(), safe))
    os.makedirs(folder, exist_ok=True)
    return folder
    
