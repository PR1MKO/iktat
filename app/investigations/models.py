import sqlalchemy as sa

from app import db
from app.utils.time_utils import now_utc


class Investigation(db.Model):
    __bind_key__ = "examination"
    __tablename__ = "investigation"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
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

    assignment_type = db.Column(
        db.Enum("INTEZETI", "SZAKĂ‰RTĹI", name="assignment_type"),
        nullable=False,
        default="INTEZETI",
    )
    assigned_expert_id = db.Column(db.Integer, index=True)
    status = db.Column(
        db.String(32),
        nullable=False,
        default="beĂ©rkezett",
        server_default=db.text("'beĂ©rkezett'"),
    )

    registration_time = db.Column(
        db.DateTime(timezone=True), default=now_utc, nullable=False
    )
    deadline = db.Column(db.DateTime(timezone=True))

    # Store user refs as plain ints (no cross-DB foreign keys)
    expert1_id = db.Column(db.Integer, index=True)
    expert2_id = db.Column(db.Integer, index=True)
    describer_id = db.Column(db.Integer, index=True)

    notes = db.relationship(
        "InvestigationNote",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    attachments = db.relationship(
        "InvestigationAttachment",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    change_logs = db.relationship(
        "InvestigationChangeLog",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Keep the historical UNIQUE name that exists in the DB already
        db.UniqueConstraint("case_number", name="ux_investigation_case_number"),
        db.Index("ix_investigation_subject_name", "subject_name"),
        db.Index("ix_investigation_institution_name", "institution_name"),
        db.Index("ix_investigation_taj_number", "taj_number"),
    )


class InvestigationNote(db.Model):
    __bind_key__ = "examination"
    __tablename__ = "investigation_note"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey("investigation.id"), nullable=False
    )
    author_id = db.Column(db.Integer, index=True, nullable=False)  # plain int
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)

    investigation = db.relationship("Investigation", back_populates="notes")


class InvestigationAttachment(db.Model):
    __bind_key__ = "examination"
    __tablename__ = "investigation_attachment"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey("investigation.id"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    uploaded_by = db.Column(db.Integer, index=True, nullable=False)  # plain int
    uploaded_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)

    investigation = db.relationship("Investigation", back_populates="attachments")


class InvestigationChangeLog(db.Model):
    __bind_key__ = "examination"
    __tablename__ = "investigation_change_log"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    investigation_id = db.Column(
        db.Integer, db.ForeignKey("investigation.id"), nullable=False
    )
    field_name = db.Column(db.String(64), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    edited_by = db.Column(db.Integer, index=True, nullable=False)  # plain int
    timestamp = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)

    investigation = db.relationship("Investigation", back_populates="change_logs")

    __table_args__ = (
        sa.Index(
            "ix_investigation_change_log_inv_id_ts",
            "investigation_id",
            "timestamp",
        ),
    )
