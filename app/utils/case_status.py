CASE_STATUS_FINAL = "lezárt"

def is_final_status(status: str) -> bool:
    return (status or "").strip().lower() == CASE_STATUS_FINAL