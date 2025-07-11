# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect
from config import Config

# ⛔️ Removed this line to prevent circular import
# from app.models import AuditLog

# Instantiate extensions
db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()
login_manager = LoginManager()

# Load environment variables from .env if present
load_dotenv()

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

    # Upload config
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

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
    Migrate(app, db)
    mail.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ✅ Local import to avoid circular reference
    from .models import User
    with app.app_context():
        from app import models

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .views.auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Exempt login route from CSRF (to avoid token error)
    csrf.exempt(auth_bp)

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

    return app

