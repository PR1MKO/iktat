from app import db
from app.investigations.utils import now_local


class Investigation(db.Model):
    __bind_key__ = 'examination'
    metadata = db.metadata

    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(16), unique=True, nullable=False)
    external_case_number = db.Column(db.String(64))
    other_identifier = db.Column(db.String(64))
    subject_name = db.Column(db.String(128), nullable=False)
    maiden_name = db.Column(db.String(128))
    investigation_type = db.Column(db.String(64))
    mother_name = db.Column(db.String(128), nullable=False)
    birth_place = db.Column(db.String(128), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    taj_number = db.Column(db.String(16), nullable=False)
    residence = db.Column(db.String(255), nullable=False)
    citizenship = db.Column(db.String(255), nullable=False)
    institution_name = db.Column(db.String(128), nullable=False)
    registration_time = db.Column(db.DateTime(timezone=True), default=now_local)
    deadline = db.Column(db.DateTime(timezone=True))
    expert1_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    expert2_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    describer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    expert1 = db.relationship('User', foreign_keys=[expert1_id])
    expert2 = db.relationship('User', foreign_keys=[expert2_id])
    describer = db.relationship('User', foreign_keys=[describer_id])

    notes = db.relationship(
        'InvestigationNote',
        back_populates='investigation',
        cascade='all, delete-orphan'
    )
    attachments = db.relationship(
        'InvestigationAttachment',
        back_populates='investigation',
        cascade='all, delete-orphan'
    )
    change_logs = db.relationship(
        'InvestigationChangeLog',
        back_populates='investigation',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.Index('ix_investigation_case_number', 'case_number'),
        db.Index('ix_investigation_subject_name', 'subject_name'),
        db.Index('ix_investigation_institution_name', 'institution_name'),
        db.Index('ix_investigation_taj_number', 'taj_number'),
        {'info': {'bind_key': 'examination'}},
    )


class InvestigationNote(db.Model):
    __bind_key__ = 'examination'
    metadata = db.metadata

    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey('investigation.id'), nullable=False
    )
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=now_local)

    investigation = db.relationship(
        'Investigation', back_populates='notes'
    )
    author = db.relationship('User')

    __table_args__ = {'info': {'bind_key': 'examination'}}


class InvestigationAttachment(db.Model):
    __bind_key__ = 'examination'
    metadata = db.metadata

    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey('investigation.id'), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(64))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=now_local)

    investigation = db.relationship(
        'Investigation', back_populates='attachments'
    )
    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    __table_args__ = {'info': {'bind_key': 'examination'}}


class InvestigationChangeLog(db.Model):
    __bind_key__ = 'examination'
    metadata = db.metadata

    id = db.Column(db.Integer, primary_key=True)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey('investigation.id'), nullable=False
    )
    field_name = db.Column(db.String(64), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    edited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=now_local)

    investigation = db.relationship(
        'Investigation', back_populates='change_logs'
    )
    editor = db.relationship('User', foreign_keys=[edited_by])

    __table_args__ = {'info': {'bind_key': 'examination'}}