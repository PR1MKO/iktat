from app.paths import (
    case_root as _case_root,
    ensure_case_folder as _ensure_case,
    ensure_investigation_folder as _ensure_invest,
)
    
def resolve_case_upload_root(app=None):
    return _case_root()

def ensure_case_folder(app, case_number: str) -> str:
    return _ensure_case(case_number)

def case_upload_dir(case_number: str) -> str:
    return _ensure_case(case_number)

def investigation_upload_dir(case_number: str) -> str:
    return _ensure_invest(case_number)

