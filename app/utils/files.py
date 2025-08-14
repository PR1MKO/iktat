import os
import re
from flask import current_app
from app.paths import case_root as _case_root, ensure_case_folder as _ensure_case

_DRIVE_ONLY_RE = re.compile(r"^[A-Za-z]:$")

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path
    
def resolve_case_upload_root(app=None):
    return _case_root()

def ensure_case_folder(app, case_number: str) -> str:
    return _ensure_case(case_number)

def case_upload_dir(case_number: str) -> str:
    return _ensure_case(case_number)

def investigation_upload_dir(case_number: str) -> str:
    # tests look under INVESTIGATION_UPLOAD_FOLDER/<case_number>
    base = current_app.config["INVESTIGATION_UPLOAD_FOLDER"]
    return ensure_dir(os.path.join(base, case_number))
