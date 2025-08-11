# app/__init__.py

import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from flask import Flask
import pytz
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect

# Load environment variables from .env if present before importing Config
load_dotenv()

from config import Config  # noqa: E402
from app.utils.time_utils import BUDAPEST_TZ  # noqa: E402

# Instantiate extensions
db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()
login_manager = LoginManager()
migrate = Migrate()
migrate_examination = Migrate()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Base configuration
    app.config.from_object(Config)
    if test_config:
        if isinstance(test_config, dict):
            app.config.update(test_config)
        else:
            app.config.from_object(test_config)

    db_name = 'test.db' if app.config.get('TESTING') else 'forensic_cases.db'
    db_path = os.path.join(app.instance_path, db_name)
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', f'sqlite:///{db_path}')
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    # Upload config (✅ This is the fix that matters)
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['INVESTIGATION_UPLOAD_FOLDER'], exist_ok=True)

    # Email config
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER')
    )

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    migrate_examination.init_app(
        app, db, directory='migrations_examination', compare_type=True, render_as_batch=True
    )
    mail.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ✅ Local import to avoid circular reference
    from .models import User
    with app.app_context():
        from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .views.auth import auth_bp
    from .routes import main_bp
    from .investigations import investigations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(investigations_bp, url_prefix='/investigations')

    from app.error_handlers import register_error_handlers
    register_error_handlers(app)

    # One-time check for essential tables
    _checked_tables = False

    @app.before_request
    def check_essential_tables_once():
        nonlocal _checked_tables
        if (
            _checked_tables or app.config.get('TESTING')
            or app.config.get('ENV') != 'production'
        ):
            return
        from sqlalchemy import inspect
        required_tables = ['user', 'case', 'change_log', 'uploaded_file']
        inspector = inspect(db.engine)
        missing = [t for t in required_tables if not inspector.has_table(t)]
        if missing:
            raise RuntimeError(f"Missing tables: {missing}")
        _checked_tables = True

    @app.route("/")
    def hello():
        return "Hello, world! Forensic Case Tracker is running."

    # Jinja filter for <input type="datetime-local">
    app.jinja_env.filters['datetimeformat'] = lambda value: value.strftime('%Y-%m-%dT%H:%M') if value else ''
    app.jinja_env.filters['getattr'] = lambda obj, name: getattr(obj, name, '')

    def localtime(value: datetime | None):
        if not value:
            return ''
        if value.tzinfo is None:
            value = value.replace(tzinfo=BUDAPEST_TZ)
        return value.astimezone(BUDAPEST_TZ).strftime('%Y-%m-%d %H:%M')

    app.jinja_env.filters['localtime'] = localtime
    app.jinja_env.globals['BUDAPEST_TZ'] = BUDAPEST_TZ

    # --- Changelog helpers -------------------------------------------------
    import re

    TOX_ORDER_RE = re.compile(
        r"^(?P<name>.+?) rendelve: (?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) [\u2013-] (?P<user>.+)$"
    )

    def parse_tox_changelog(value: str | None):
        if not value:
            return None
        m = TOX_ORDER_RE.match(value.strip())
        if not m:
            return None
        return {
            "name": m.group("name"),
            "ts": m.group("ts"),
            "user": m.group("user"),
        }

    app.jinja_env.filters['parse_tox_changelog'] = parse_tox_changelog

    NOTE_RE = re.compile(
        r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) [\u2013-] (?P<user>[^\]]+)\]\s*(?P<text>.*)$"
    )

    def parse_note_changelog(value: str | None):
        if not value:
            return None
        m = NOTE_RE.match(value.strip())
        if not m:
            return None
        return {
            "ts": m.group("ts"),
            "user": m.group("user"),
            "text": m.group("text"),
        }

    app.jinja_env.filters['parse_note_changelog'] = parse_note_changelog

    # Logging setup
    if not app.debug and not app.testing:
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'), maxBytes=10240, backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Logging initialized.')

    return app
