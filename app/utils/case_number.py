from sqlalchemy import func
from app.utils.time_utils import now_local
from app.models import Case


def generate_case_number_for_year(session, year: int | None = None) -> str:
    """Return next case number in format 'B:0001/YYYY'."""
    y = year or now_local().year
    count_for_year = (
        session.query(func.count(Case.id))
        .filter(func.strftime("%Y", Case.registration_time) == str(y))
        .scalar()
        or 0
    )
    seq = count_for_year + 1
    while True:
        candidate = f"B:{seq:04d}/{y}"
        exists = session.query(Case.id).filter(Case.case_number == candidate).first()
        if not exists:
            return candidate
        seq += 1