from pathlib import Path
from flask import current_app

def _default_case_root() -> Path:
    return Path(current_app.instance_path) / "uploads_cases"

def _default_investigation_root() -> Path:
    return Path(current_app.instance_path) / "uploads_investigations"

def case_root() -> Path:
    raw = current_app.config.get("CASE_UPLOAD_FOLDER")
    root = Path(raw) if raw else _default_case_root()
    root.mkdir(parents=True, exist_ok=True)
    return root

def investigation_root() -> Path:
    raw = current_app.config.get("INVESTIGATION_UPLOAD_FOLDER")
    root = Path(raw) if raw else _default_investigation_root()
    root.mkdir(parents=True, exist_ok=True)
    return root

def file_safe_case_number(n: str) -> str:
    return n.replace(":", "-").replace("/", "-").strip(" .")

def ensure_case_folder(case_number: str) -> Path:
    safe = file_safe_case_number(case_number)
    p = case_root() / safe
    p.mkdir(parents=True, exist_ok=True)
    return p

def case_folder_name(case_number: str) -> str:
    return file_safe_case_number(case_number)

def ensure_investigation_folder(case_number: str) -> Path:
    safe = case_number.replace(":", "-").replace("/", "-").strip(" .")
    p = investigation_root() / safe
    p.mkdir(parents=True, exist_ok=True)
    return p

def case_upload_dir(case_number: str) -> str:
    return str(ensure_case_folder(case_number))

def investigation_upload_dir(case_number: str) -> str:
    return str(ensure_investigation_folder(case_number))
