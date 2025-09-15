from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
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
    subject_name = StringField("Vizsgált személy neve", validators=[DataRequired()])
    maiden_name = StringField("Leánykori neve", validators=[Optional()])
    mother_name = StringField("Anyja neve", validators=[DataRequired()])
    birth_place = StringField("Születési hely", validators=[DataRequired()])
    birth_date = DateField(
        "Születési idő", format="%Y-%m-%d", validators=[DataRequired()]
    )
    taj_number = StringField("TAJ szám", validators=[DataRequired()])
    residence = StringField("Lakcíme", validators=[DataRequired()])
    citizenship = StringField("Állampolgársága", validators=[DataRequired()])
    institution_name = StringField("Beküldő intézmény", validators=[DataRequired()])
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
    external_case_number = StringField("Külső ügyirat szám", validators=[Optional()])
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

    submit = SubmitField("Vizsgálat létrehozása")

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


INV_CATEGORY_CHOICES = [
    ("végzés", "Végzés"),
    ("jegyzőkönyv", "Jegyzőkönyv"),
    ("egyéb", "Egyéb"),
]


class FileUploadForm(FlaskForm):
    # Allow arbitrary values server-side while keeping UI suggestions
    category = SelectField(
        "Kategória",
        choices=INV_CATEGORY_CHOICES,
        validators=[DataRequired(message="Kategória megadása kötelező.")],
        validate_choice=False,
    )
    file = FileField("Fájl", validators=[FileRequired()])


class InvestigationNoteForm(FlaskForm):
    text = TextAreaField("Megjegyzés", validators=[DataRequired()])
