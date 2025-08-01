# app/models.py

from flask_login import UserMixin, current_user
from app import db                # ← your single SQLAlchemy instance
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz
from app.utils.time_utils import BUDAPEST_TZ
from sqlalchemy import event, inspect

class User(db.Model, UserMixin):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    screen_name   = db.Column(db.String(128), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role          = db.Column(db.String(20), nullable=False)
    default_leiro_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    default_leiro = db.relationship('User', foreign_keys=[default_leiro_id], lazy='joined')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Case(db.Model):
    id                   = db.Column(db.Integer, primary_key=True)
    case_number          = db.Column(db.String(32), unique=True, nullable=False)
    deceased_name        = db.Column(db.String(128))
    case_type            = db.Column(db.String(64))
    status               = db.Column(db.String(32), nullable=False, default='new')
    institution_name     = db.Column(db.String(128))
    external_case_number = db.Column(db.String(64))
    temp_id             = db.Column(db.String(64))
    birth_date           = db.Column(db.Date)
    registration_time    = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(BUDAPEST_TZ)
    )
    deadline             = db.Column(db.DateTime(timezone=True))
    expert_1             = db.Column(db.String(128))
    expert_2             = db.Column(db.String(128))
    describer            = db.Column(db.String(128))
    tox_expert          = db.Column(db.String(128))
    tox_completed       = db.Column(db.Boolean, default=False)
    assigned_office      = db.Column(db.String(64))
    assigned_signatory   = db.Column(db.String(64))
    assigned_pathologist = db.Column(db.String(64))
    notes                = db.Column(db.Text)
    uploaded_files       = db.Column(db.Text)
    tox_orders           = db.Column(db.Text)

    # --- TOVÁBBI ADATOK ---
    beerk_modja = db.Column(db.String(32))   # Beérkezés módja
    poszeidon      = db.Column(db.String(64))    # Poszeidon
    lanykori_nev   = db.Column(db.String(128))   # Elhunyt lánykori neve
    mother_name    = db.Column('anyja_neve', db.String(128))  # Anyja neve
    szul_hely      = db.Column(db.String(128))   # Szuletési hely
    taj_szam       = db.Column(db.String(16))    # TAJ szám

    # --- TOX + SZERVVIZSGÁLATOK ---

    alkohol_ver              = db.Column(db.String(128))
    alkohol_ver_ordered      = db.Column(db.Boolean, default=False)
    alkohol_vizelet          = db.Column(db.String(128))
    alkohol_vizelet_ordered  = db.Column(db.Boolean, default=False)
    alkohol_liquor           = db.Column(db.String(128))
    alkohol_liquor_ordered   = db.Column(db.Boolean, default=False)
    egyeb_alkohol            = db.Column(db.Text)
    egyeb_alkohol_ordered    = db.Column(db.Boolean, default=False)

    tox_gyogyszer_ver        = db.Column(db.String(128))
    tox_gyogyszer_ver_ordered = db.Column(db.Boolean, default=False)
    tox_gyogyszer_vizelet     = db.Column(db.String(128))
    tox_gyogyszer_vizelet_ordered = db.Column(db.Boolean, default=False)
    tox_gyogyszer_gyomor      = db.Column(db.String(128))
    tox_gyogyszer_gyomor_ordered = db.Column(db.Boolean, default=False)
    tox_gyogyszer_maj         = db.Column(db.String(128))
    tox_gyogyszer_maj_ordered = db.Column(db.Boolean, default=False)

    tox_kabitoszer_ver        = db.Column(db.String(128))
    tox_kabitoszer_ver_ordered = db.Column(db.Boolean, default=False)
    tox_kabitoszer_vizelet     = db.Column(db.String(128))
    tox_kabitoszer_vizelet_ordered = db.Column(db.Boolean, default=False)

    tox_cpk            = db.Column(db.String(128))
    tox_cpk_ordered    = db.Column(db.Boolean, default=False)
    tox_szarazanyag    = db.Column(db.String(128))
    tox_szarazanyag_ordered = db.Column(db.Boolean, default=False)
    tox_diatoma        = db.Column(db.String(128))
    tox_diatoma_ordered = db.Column(db.Boolean, default=False)
    tox_co             = db.Column(db.String(128))
    tox_co_ordered     = db.Column(db.Boolean, default=False)

    egyeb_tox          = db.Column(db.Text)
    egyeb_tox_ordered  = db.Column(db.Boolean, default=False)

    sziv_spec = db.Column(db.Boolean, default=False)
    sziv_immun = db.Column(db.Boolean, default=False)
    tudo_spec = db.Column(db.Boolean, default=False)
    tudo_immun = db.Column(db.Boolean, default=False)
    maj_spec = db.Column(db.Boolean, default=False)
    maj_immun = db.Column(db.Boolean, default=False)
    vese_spec = db.Column(db.Boolean, default=False)
    vese_immun = db.Column(db.Boolean, default=False)
    agy_spec = db.Column(db.Boolean, default=False)
    agy_immun = db.Column(db.Boolean, default=False)
    mellekvese_spec = db.Column(db.Boolean, default=False)
    mellekvese_immun = db.Column(db.Boolean, default=False)
    pajzsmirigy_spec = db.Column(db.Boolean, default=False)
    pajzsmirigy_immun = db.Column(db.Boolean, default=False)
    hasnyalmirigy_spec = db.Column(db.Boolean, default=False)
    hasnyalmirigy_immun = db.Column(db.Boolean, default=False)
    lep_spec = db.Column(db.Boolean, default=False)
    lep_immun = db.Column(db.Boolean, default=False)
    egyeb_szerv = db.Column(db.String(128))
    egyeb_szerv_spec = db.Column(db.Boolean, default=False)
    egyeb_szerv_immun = db.Column(db.Boolean, default=False)

    # --- Halotti bizonyítvány adatok ---
    halalt_megallap_pathologus = db.Column(db.Boolean, default=False)
    halalt_megallap_kezeloorvos = db.Column(db.Boolean, default=False)
    halalt_megallap_mas_orvos = db.Column(db.Boolean, default=False)
    boncolas_tortent = db.Column(db.Boolean, default=False)
    varhato_tovabbi_vizsgalat = db.Column(db.Boolean, default=False)
    kozvetlen_halalok = db.Column(db.String(256))
    kozvetlen_halalok_ido = db.Column(db.String(64))
    alapbetegseg_szovodmenyei = db.Column(db.String(256))
    alapbetegseg_szovodmenyei_ido = db.Column(db.String(64))
    alapbetegseg = db.Column(db.String(256))
    alapbetegseg_ido = db.Column(db.String(64))
    kiserobetegsegek = db.Column(db.Text)
    
    certificate_generated = db.Column(db.Boolean, default=False)
    certificate_generated_at = db.Column(db.DateTime(timezone=True))

    tox_doc_generated = db.Column(db.Boolean, default=False)
    tox_doc_generated_at = db.Column(db.DateTime(timezone=True))
    tox_doc_generated_by = db.Column(db.String)

    uploaded_file_records = db.relationship(
        'UploadedFile',
        order_by='UploadedFile.upload_time.desc()',
        back_populates='case',
        cascade='all, delete-orphan'
    )

    @property
    def formatted_deadline(self) -> str:
        """Deadline formatted for display in templates."""
        if not self.deadline:
            return ''
        dt = self.deadline
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.utc)
        return dt.astimezone(BUDAPEST_TZ).strftime('%Y-%m-%d')
        
    def __repr__(self):
        return f'<Case {self.case_number} - {self.deceased_name}>'

class AuditLog(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(BUDAPEST_TZ),
        index=True,
        nullable=False,
    )
    user_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username  = db.Column(db.String(64), nullable=False)
    role      = db.Column(db.String(20), nullable=False)
    action    = db.Column(db.String(256), nullable=False)
    details   = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.timestamp} {self.username} {self.action}>'

class ChangeLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    case_id    = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    field_name = db.Column(db.String(64), nullable=False)
    old_value  = db.Column(db.Text)
    new_value  = db.Column(db.Text)
    edited_by  = db.Column(db.String(64), nullable=False)
    timestamp  = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(BUDAPEST_TZ)
    )

    case = db.relationship('Case', backref=db.backref('change_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<ChangeLog {self.field_name}: {self.old_value} → {self.new_value}>'

_TRACKED_FIELDS = [
    'deceased_name', 'case_type', 'status', 'institution_name',
    'external_case_number', 'birth_date', 'registration_time',
    'deadline', 'expert_1', 'expert_2', 'describer',
    'tox_expert',
    'assigned_office', 'assigned_signatory', 'assigned_pathologist',
    'notes', 'uploaded_files', 'tox_orders'
]

@event.listens_for(Case, 'before_update')
def _audit_case_changes(mapper, connection, target):
    """Record changes to Case fields in ChangeLog without using Session.add."""    
    state = inspect(target)
    log_entries = []
    
    for field in _TRACKED_FIELDS:
        hist = state.attrs[field].history
        if not hist.has_changes():
            continue
            
        old = hist.deleted[0] if hist.deleted else None
        new = hist.added[0] if hist.added else None
        
        if field in ("tox_orders", "notes"):
            old_lines = old.splitlines() if old else []
            new_lines = new.splitlines() if new else []
            added = new_lines[len(old_lines):]
            for line in added:
                log_entries.append({
                    "case_id": target.id,
                    "field_name": field,
                    "old_value": None,
                    "new_value": line,
                    "edited_by": (
                        getattr(current_user, "screen_name", None)
                        or getattr(current_user, "username", "system")
                    ),
                    "timestamp": datetime.now(BUDAPEST_TZ),
                })
            continue

        if old != new:
            log_entries.append({
                "case_id": target.id,
                "field_name": field,
                "old_value": str(old) if old is not None else None,
                "new_value": str(new) if new is not None else None,
                "edited_by": (
                    getattr(current_user, "screen_name", None)
                    or getattr(current_user, "username", "system")
                ),
                "timestamp": datetime.now(BUDAPEST_TZ),
            })

    if log_entries:
        connection.execute(ChangeLog.__table__.insert(), log_entries)           

class UploadedFile(db.Model):
    __tablename__ = 'uploaded_file'
    id          = db.Column(db.Integer, primary_key=True)
    case_id     = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    filename    = db.Column(db.String(256), nullable=False)
    upload_time = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(BUDAPEST_TZ),
        nullable=False,
    )
    uploader    = db.Column(db.String(64), nullable=False)
    category    = db.Column(db.String(50), nullable=False)

    case = db.relationship('Case', back_populates='uploaded_file_records')

    def __repr__(self):
        return f'<UploadedFile {self.filename} by {self.uploader} on {self.upload_time}>'

class TaskMessage(db.Model):
    """Persistent notification for assigned tasks."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(BUDAPEST_TZ)
    )
    seen = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='task_messages')
    case = db.relationship('Case')

