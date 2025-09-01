# app/investigations/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    DateField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Optional, ValidationError


class InvestigationForm(FlaskForm):
    subject_name = StringField("Név", validators=[DataRequired()])
    maiden_name = StringField("Leánykori név", validators=[Optional()])
    mother_name = StringField("Anyja neve", validators=[DataRequired()])
    birth_place = StringField("Születési hely", validators=[DataRequired()])
    birth_date = DateField(
        "Születési idő", format="%Y-%m-%d", validators=[DataRequired()]
    )
    taj_number = StringField("TAJ szám", validators=[DataRequired()])
    residence = StringField("Lakcím", validators=[DataRequired()])
    citizenship = StringField("Állampolgárság", validators=[DataRequired()])
    institution_name = StringField("Intézmény neve", validators=[DataRequired()])
    investigation_type = SelectField(
        "Vizsgálat típusa",
        choices=[
            ("", "-- Válasszon --"),
            ("type1", "Típus 1"),
            ("type2", "Típus 2"),
            ("type3", "Típus 3"),
        ],
        validators=[DataRequired()],
    )
    external_case_number = StringField("Külső ügyszám", validators=[Optional()])
    other_identifier = StringField("Egyéb azonosító", validators=[Optional()])

    assignment_type = RadioField(
        "Végrehajtás módja",
        choices=[
            ("INTEZETI", "Intézeti"),
            ("SZAKÉRTŐI", "Szakértői"),
        ],
        default="INTEZETI",
        validators=[DataRequired()],
    )
    assigned_expert_id = SelectField(
        "Szakértő",
        choices=[(0, "— Válasszon —")],
        coerce=int,
        default=0,
        validators=[Optional()],
    )

    submit = SubmitField("Mentés")

    def validate(self, *args, **kwargs):
        valid = super().validate(*args, **kwargs)
        if not valid:
            return False
        # Legalább az egyik azonosító kötelező
        if not self.external_case_number.data and not self.other_identifier.data:
            msg = "Legalább az egyik azonosítót meg kell adni."
            self.external_case_number.errors.append(msg)
            self.other_identifier.errors.append(msg)
            return False
        return True

    def validate_assigned_expert_id(self, field):
        if self.assignment_type.data == "SZAKÉRTŐI" and field.data == 0:
            raise ValidationError("Szakértő kiválasztása kötelező.")


class FileUploadForm(FlaskForm):
    category = SelectField(
        "Kategória",
        choices=[
            ("option1", "Opció 1"),
            ("option2", "Opció 2"),
            ("option3", "Opció 3"),
        ],
        validators=[DataRequired()],
    )
    file = FileField("Fájl", validators=[DataRequired()])


class InvestigationNoteForm(FlaskForm):
    text = TextAreaField("Megjegyzés", validators=[DataRequired()])
