import pytest
from datetime import date

from app import db
from app.models import Case
from app.investigations.models import Investigation


def test_case_status_default(app):
    with app.app_context():
        c = Case(case_number="T-PK-1")
        db.session.add(c)
        db.session.commit()
        assert c.status == 'new'


def test_case_pk_autoincrement(app):
    with app.app_context():
        a = Case(case_number="T-PK-2", status='beérkezett')
        b = Case(case_number="T-PK-3", status='beérkezett')
        db.session.add_all([a, b])
        db.session.commit()
        assert isinstance(a.id, int) and isinstance(b.id, int)
        assert b.id > a.id


def test_investigation_pk_autoincrement(app):
    with app.app_context():
        inv1 = Investigation(
            case_number="V-PK-1",
            subject_name="X",
            mother_name="M",
            birth_place="BP",
            birth_date=date(2000, 1, 1),
            taj_number="123456789",
            residence="Res",
            citizenship="HU",
            institution_name="Inst",
        )
        inv2 = Investigation(
            case_number="V-PK-2",
            subject_name="Y",
            mother_name="M",
            birth_place="BP",
            birth_date=date(2000, 1, 1),
            taj_number="987654321",
            residence="Res",
            citizenship="HU",
            institution_name="Inst",
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()
        assert inv2.id > inv1.id