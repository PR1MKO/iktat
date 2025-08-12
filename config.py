# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    # NOTE: UPLOAD paths are FORCE-set in app/__init__.py to live under app.root_path.
    # Keeping these here for completeness, but they get overridden in create_app().
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    SQLALCHEMY_BINDS = {
        'examination': os.environ.get('EXAMINATION_DATABASE_URL', 'sqlite:///examination.db')
    }

    INVESTIGATION_UPLOAD_FOLDER = os.environ.get(
        'INVESTIGATION_UPLOAD_FOLDER',
        os.path.join(BASE_DIR, 'uploads_investigations')
    )

    TRACK_USER_ACTIVITY = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    TRACK_USER_ACTIVITY = False

    @staticmethod
    def init_app(app):
        pass
