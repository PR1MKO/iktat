from app.paths import (
    case_root as case_root_path,
    ensure_case_folder as ensure_case_path,
    ensure_investigation_folder as ensure_invest_folder_path,
)
    
def resolve_case_upload_root(app=None) -> str:
    return str(case_root_path())

def ensure_case_folder(app, case_number: str) -> str:
    return str(ensure_case_path(case_number))

def case_upload_dir(case_number: str) -> str:
    return str(ensure_case_path(case_number))

def investigation_upload_dir(case_number: str) -> str:
    return _ensure_invest(case_number)    return str(ensure_invest_folder_path(case_number))
