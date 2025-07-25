# app/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SelectField, TextAreaField, DateField,
    DateTimeLocalField
)
from wtforms.validators import DataRequired, Optional

class EditCaseForm(FlaskForm):
    deceased_name = StringField(
        'Elhunyt neve',
        validators=[DataRequired()]
    )
    case_type = SelectField(
        'Típus',
        choices=[('', '-- Válasszon --')] + [
            (v, v) for v in ['hatósági', 'klinikai', 'igazságügyi', 'kórboncolási', 'elengedés']
        ],
        validators=[DataRequired()]
    )
    status = SelectField(
        'Állapot',
        choices=[('', '-- Válasszon --')] + [
            (v, v) for v in [
                'beérkezett','boncolva-leírónál','boncolva-orvosnál',
                'leiktatva','szignálva','lezárva','lejárt',
                'rendőrségre küldve','számla megérkezett','postafakkba'
            ]
        ],
        validators=[DataRequired()]
    )
    institution_name = StringField('Intézmény neve', validators=[Optional()])
    external_case_number = StringField('Külső ügyirat szám', validators=[Optional()])
    birth_date = DateField('Születési idő', format='%Y-%m-%d', validators=[Optional()])
    registration_time = DateTimeLocalField(
        'Regisztrálva',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired()]
    )
    # deadline is shown but not editable
    expert_1 = SelectField('Szakértő 1', coerce=str, validators=[Optional()])
    expert_2 = SelectField('Szakértő 2', coerce=str, validators=[Optional()])
    describer = SelectField('Leíró', coerce=str, validators=[Optional()])
    notes = TextAreaField('Megjegyzés', validators=[Optional()])

class CaseIdentifierForm(FlaskForm):
    external_id = StringField("Külső ügyirat szám")
    temp_id = StringField("Egyéb azonosító")

    def validate(self, *args, **kwargs):
        valid = super().validate(*args, **kwargs)
        if not valid:
            return False
        if not self.external_id.data and not self.temp_id.data:
            msg = "Legalább az egyik azonosítót meg kell adni."
            self.external_id.errors.append(msg)
            self.temp_id.errors.append(msg)
            return False
        return True
