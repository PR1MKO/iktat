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

def ensure_case_folder(case_number: str) -> str:
    folder = _norm(os.path.join(case_root(), case_number))
    os.makedirs(folder, exist_ok=True)
    return folder