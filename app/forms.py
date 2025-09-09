# app/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DateTimeLocalField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class AdminUserForm(FlaskForm):
    username = StringField(
        "Felhasználónév", validators=[DataRequired(), Length(max=64)]
    )
    screen_name = StringField(
        "Megjelenítendő név", validators=[Optional(), Length(max=64)]
    )
    full_name = StringField("Teljes név", validators=[Optional(), Length(max=128)])
    password = PasswordField("Jelszó", validators=[Optional()])
    role = SelectField(
        "Szerepkör",
        choices=[
            ("admin", "Admin"),
            ("iroda", "Iroda"),
            ("pénzügy", "Pénzügy"),
            ("szignáló", "Szignáló"),
            ("szakértő", "Szakértő"),
            ("leíró", "Leíró"),
            ("toxi", "toxi"),
        ],
        validators=[DataRequired()],
    )
    default_leiro_id = SelectField(
        "Default leíró",
        coerce=int,
        choices=[],
        default=0,
        render_kw={"disabled": True},
        validate_choice=False,
    )

    def validate_default_leiro_id(self, field):
        """
        Require default_leiro_id when role is 'szakértő'.
        Uses WTForms' default DataRequired message without customization.
        """
        if field.data is None:
            field.data = 0
        if getattr(self.role, "data", None) == "szakértő":
            DataRequired()(self, field)
            valid_ids = [choice[0] for choice in field.choices]
            if field.data not in valid_ids:
                raise ValidationError(field.gettext("Not a valid choice"))


class EditCaseForm(FlaskForm):
    deceased_name = StringField("Elhunyt neve", validators=[DataRequired()])
    case_type = SelectField(
        "Típus",
        choices=[("", "-- Válasszon --")]
        + [
            (v, v)
            for v in [
                "hatósági",
                "klinikai",
                "igazságügyi",
                "kórboncolási",
                "elengedés",
            ]
        ],
        validators=[DataRequired()],
    )
    status = SelectField(
        "Állapot",
        choices=[("", "-- Válasszon --")]
        + [
            (v, v)
            for v in [
                "beérkezett",
                "boncolva-leírónál",
                "boncolva-orvosnál",
                "leiktatva",
                "szignálva",
                "lezárt",
                "rendőrségre küldve",
                "számla megérkezett",
                "postafakkba",
            ]
        ],
        validators=[DataRequired()],
    )
    institution_name = StringField("Intézmény neve", validators=[Optional()])
    external_case_number = StringField("Külső ügyirat szám", validators=[Optional()])
    birth_date = DateField("Születési idő", format="%Y-%m-%d", validators=[Optional()])
    registration_time = DateTimeLocalField(
        "Regisztrálva", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    # deadline is shown but not editable
    expert_1 = SelectField("Szakértő 1", coerce=str, validators=[Optional()])
    expert_2 = SelectField("Szakértő 2", coerce=str, validators=[Optional()])
    describer = SelectField("Leíró", coerce=str, validators=[Optional()])
    notes = TextAreaField("Megjegyzés", validators=[Optional()])


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
