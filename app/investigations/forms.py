# app/investigations/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField
from wtforms.fields import DateField, DateTimeLocalField
from flask_wtf.file import FileField
from wtforms.validators import DataRequired, Optional, Length


class InvestigationForm(FlaskForm):
    subject_name = StringField('Név', validators=[DataRequired(), Length(max=128)])
    maiden_name = StringField('Leánykori név', validators=[Optional(), Length(max=128)])
    mother_name = StringField('Anyja neve', validators=[DataRequired(), Length(max=128)])
    birth_place = StringField('Születési hely', validators=[DataRequired(), Length(max=128)])
    birth_date = DateField('Születési idő', format='%Y-%m-%d', validators=[DataRequired()])
    taj_number = StringField('TAJ szám', validators=[DataRequired(), Length(max=16)])
    residence = StringField('Lakcím', validators=[DataRequired(), Length(max=255)])
    citizenship = StringField('Állampolgárság', validators=[DataRequired(), Length(max=255)])
    institution_name = StringField('Intézmény neve', validators=[DataRequired(), Length(max=128)])

    investigation_type = SelectField(
        'Vizsgálat típusa',
        choices=[
            ('', '-- Válasszon --'),
            ('type1', 'Típus 1'),
            ('type2', 'Típus 2'),
            ('type3', 'Típus 3'),
        ],
        validators=[DataRequired()],
    )

    deadline = DateTimeLocalField('Határidő', format='%Y-%m-%dT%H:%M', validators=[Optional()])

    external_case_number = StringField('Külső ügyszám', validators=[Optional(), Length(max=64)])
    other_identifier = StringField('Egyéb azonosító', validators=[Optional(), Length(max=64)])

    # Populate choices in the view before render
    expert1_id = SelectField('Szakértő 1', coerce=int, validators=[Optional()], choices=[(0, '— Nincs —')])
    expert2_id = SelectField('Szakértő 2', coerce=int, validators=[Optional()], choices=[(0, '— Nincs —')])
    describer_id = SelectField('Leíró',     coerce=int, validators=[Optional()], choices=[(0, '— Nincs —')])

    def validate(self, *args, **kwargs):
        valid = super().validate(*args, **kwargs)
        if not valid:
            return False
        if not self.external_case_number.data and not self.other_identifier.data:
            msg = 'Legalább az egyik azonosítót meg kell adni.'
            self.external_case_number.errors.append(msg)
            self.other_identifier.errors.append(msg)
            return False
        return True


class FileUploadForm(FlaskForm):
    category = SelectField(
        'Kategória',
        choices=[
            ('option1', 'Opció 1'),
            ('option2', 'Opció 2'),
            ('option3', 'Opció 3'),
        ],
        validators=[DataRequired()],
    )
    file = FileField('Fájl', validators=[DataRequired()])


class InvestigationNoteForm(FlaskForm):
    text = TextAreaField('Megjegyzés', validators=[DataRequired()])
