# app/utils/files.py
from .paths import ensure_case_folder, ensure_investigation_folder


def case_upload_dir(case_number: str) -> str:
    return str(ensure_case_folder(case_number))


def investigation_upload_dir(case_number: str) -> str:
    return str(ensure_investigation_folder(case_number))
