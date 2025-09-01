# config.py
import os

# Try to load optional instance config for secrets (not tracked in VCS)
instance_cfg = None
try:
    import instance.config as instance_cfg  # type: ignore
except Exception:  # pragma: no cover - instance config is optional
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or getattr(
        instance_cfg, "SECRET_KEY", None
    )
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # Optional upload folder overrides (defaults computed from instance path)
    CASE_UPLOAD_FOLDER = os.environ.get("CASE_UPLOAD_FOLDER")
    INVESTIGATION_UPLOAD_FOLDER = os.environ.get("INVESTIGATION_UPLOAD_FOLDER")

    SQLALCHEMY_BINDS = {
        "examination": os.environ.get(
            "EXAMINATION_DATABASE_URL", "sqlite:///examination.db"
        )
    }

    TRACK_USER_ACTIVITY = True

    NO_STORE_HEADERS_ENABLED = True
    BFCACHE_RELOAD_ENABLED = True
    STRICT_PRG_ENABLED = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    TRACK_USER_ACTIVITY = False
    # 👇 ensure SQLAlchemy doesn’t expire objects after commit in tests
    SQLALCHEMY_SESSION_OPTIONS = {"expire_on_commit": False}

    @staticmethod
    def init_app(app):
        pass
