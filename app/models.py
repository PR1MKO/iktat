from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(32), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default='new')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    assigned_office = db.Column(db.String(64))      # iroda
    assigned_signatory = db.Column(db.String(64))   # szig
    assigned_pathologist = db.Column(db.String(64)) # szak
    notes = db.Column(db.Text)
    # You can add more fields here as needed for your workflow
