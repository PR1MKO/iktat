# app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect

# ← 1) Instantiate extensions before anything else
db    = SQLAlchemy()
mail  = Mail()
csrf  = CSRFProtect()

def create_app():
    # Use Flask's instance folder for a persistent DB file
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, 'forensic_cases.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY']                    = os.environ.get('SECRET_KEY', 'supersecretkey')

    # Upload configuration
    app.config['UPLOAD_FOLDER']      = os.path.join(app.root_path, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Email configuration
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='kiss.istvan.professional@gmail.com',
        MAIL_PASSWORD='zjiyimdcsfvqyaph',
        MAIL_DEFAULT_SENDER='kiss.istvan.professional@gmail.com'
    )

    # ← 2) Initialize each extension with the app
    db.init_app(app)
    Migrate(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    # ← 3) Login manager setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ← 4) Import models *after* db is initialized to avoid circular imports
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ← 4b) Exempt login route from CSRF (so POST /login doesn’t require a token)
    csrf.exempt('auth.login')

    # ← 5) Now import and register your blueprints
    from .views.auth import auth_bp
    from .routes       import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

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
        required_tables = [
            'user', 'case', 'change_log', 'uploaded_file'
        ]
        inspector = inspect(db.engine)
        missing = [t for t in required_tables if not inspector.has_table(t)]
        if missing:
            raise RuntimeError(f"Missing tables: {missing}")
        _checked_tables = True

    @app.route("/")
    def hello():
        return "Hello, world! Forensic Case Tracker is running."

    # ← 6) Jinja filter for <input type="datetime-local">
    def datetimeformat(value):
        return value.strftime('%Y-%m-%dT%H:%M') if value else ''
    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # ← 7) Register a working getattr filter for dynamic template access
    def safe_getattr(obj, name):
        return getattr(obj, name, '')
    app.jinja_env.filters['getattr'] = safe_getattr

    return app
