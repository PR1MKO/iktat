from datetime import date

from app.investigations.forms import InvestigationForm
from app.utils.time_utils import fmt_date


def _base_form_data():
    return {
        "subject_name": "Teszt Alany",
        "mother_name": "Teszt Anya",
        "birth_place": "Budapest",
        "birth_date": "2000-01-02",
        "taj_number": "123456789",
        "residence": "Cím",
        "citizenship": "magyar",
        "institution_name": "Intézet",
        "investigation_type": "type1",
    }


def test_investigation_form_requires_identifier(app):
    data = _base_form_data()
    data.update({"external_case_number": "", "other_identifier": ""})
    form = InvestigationForm(data=data)
    assert not form.validate()
    assert form.external_case_number.errors
    assert form.other_identifier.errors


def test_investigation_form_with_identifier_valid(app):
    data = _base_form_data()
    data.update({"external_case_number": "ABC123", "other_identifier": ""})
    form = InvestigationForm(data=data)
    assert form.validate()


def test_fmt_date_formats_date():
    d = date(2020, 1, 2)
    assert fmt_date(d) == "2020.01.02"
    assert fmt_date(None) == ""
