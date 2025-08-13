import os
from flask import current_app

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def case_upload_dir(case_number: str) -> str:
    # tests look under <app.root>/uploads/<case_number>
    base = current_app.config["UPLOAD_FOLDER"]
    return ensure_dir(os.path.join(base, case_number))

def investigation_upload_dir(case_number: str) -> str:
    # tests look under INVESTIGATION_UPLOAD_FOLDER/<case_number>
    base = current_app.config["INVESTIGATION_UPLOAD_FOLDER"]
    return ensure_dir(os.path.join(base, case_number))
