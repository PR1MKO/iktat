from sqlalchemy.exc import IntegrityError
from app.utils.time_utils import now_local


def generate_case_number(db_session) -> str:
    """Generate unique case number V:0001/YYYY for investigations."""
    from app.investigations.models import Investigation

    year = now_local().year
    pattern = f"V:%/{year}"
    while True:
        last = (
            db_session.query(Investigation.case_number)
            .filter(Investigation.case_number.like(pattern))
            .order_by(Investigation.case_number.desc())
            .first()
        )
        last_num = int(last[0][2:6]) if last else 0
        case_number = f"V:{last_num + 1:04d}/{year}"
        try:
            exists = (
                db_session.query(Investigation.id)
                .filter_by(case_number=case_number)
                .first()
            )
            if exists is None:
                return case_number
            raise IntegrityError(None, None, None)
        except IntegrityError:
            db_session.rollback()
            continue