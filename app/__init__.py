import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge

# Load environment variables early
load_dotenv()

from app.utils.time_utils import BUDAPEST_TZ, fmt_date  # noqa: E402
from config import Config  # noqa: E402

# Instantiate extensions
db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()
login_manager = LoginManager()
migrate = Migrate()
migrate_examination = Migrate()


def create_app(test_config=None):
    flask_app = Flask(__name__, instance_relative_config=True)
    os.makedirs(flask_app.instance_path, exist_ok=True)

    # Base configuration
    flask_app.config.from_object(Config)
    if test_config:
        if isinstance(test_config, dict):
            flask_app.config.update(test_config)
        else:
            flask_app.config.from_object(test_config)

    # ✅ SECRET_KEY fix
    flask_app.config["SECRET_KEY"] = (
        os.environ.get("SECRET_KEY") or "dev-secret-key-123"
    )

    # --- Databases ---------------------------------------------------------
    main_db_name = "test.db" if flask_app.config.get("TESTING") else "forensic_cases.db"
    main_db_path = os.path.join(flask_app.instance_path, main_db_name)
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{main_db_path}"
    flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    exam_db_name = (
        "test_examination.db" if flask_app.config.get("TESTING") else "examination.db"
    )
    exam_db_path = os.path.join(flask_app.instance_path, exam_db_name)
    exam_url = os.getenv("EXAMINATION_DATABASE_URL", f"sqlite:///{exam_db_path}")
    binds = dict(flask_app.config.get("SQLALCHEMY_BINDS") or {})
    binds["examination"] = exam_url
    flask_app.config["SQLALCHEMY_BINDS"] = binds

    flask_app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    flask_app.config.setdefault(
        "UPLOAD_CASES_ROOT", Path(flask_app.instance_path) / "uploads_cases"
    )
    flask_app.config.setdefault(
        "UPLOAD_INVESTIGATIONS_ROOT",
        Path(flask_app.instance_path) / "uploads_investigations",
    )
    flask_app.config.setdefault(
        "CASE_UPLOAD_FOLDER", str(flask_app.config["UPLOAD_CASES_ROOT"])
    )
    flask_app.config.setdefault(
        "INVESTIGATION_UPLOAD_FOLDER",
        str(flask_app.config["UPLOAD_INVESTIGATIONS_ROOT"]),
    )
    Path(flask_app.config["UPLOAD_CASES_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(flask_app.config["UPLOAD_INVESTIGATIONS_ROOT"]).mkdir(
        parents=True, exist_ok=True
    )

    # --- Email config ------------------------------------------------------
    flask_app.config.update(
        MAIL_SERVER=flask_app.config.get("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=int(flask_app.config.get("MAIL_PORT", 587)),
        MAIL_USE_TLS=(
            True
            if str(flask_app.config.get("MAIL_USE_TLS", "1")).lower() in ("1", "true")
            else False
        ),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER"),
    )

    # Init extensions
    db.init_app(flask_app)

    # 🔒 Force-load ALL models into metadata (core first, then features)
    # isort: off
    import app.models_all  # noqa: F401
    import importlib

    inv_mod = importlib.import_module("app.investigations.models")  # noqa: F401
    # 🩹 HOTFIX: if investigations tables were attached to a different MetaData,
    # remap them into THIS db.metadata so Alembic sees them.
    try:
        _classes = [
            getattr(inv_mod, "Investigation", None),
            getattr(inv_mod, "InvestigationNote", None),
            getattr(inv_mod, "InvestigationAttachment", None),
            getattr(inv_mod, "InvestigationChangeLog", None),
        ]
        for _cls in filter(None, _classes):
            _t = getattr(_cls, "__table__", None)
            if _t is not None and _t.metadata is not db.metadata:
                _cls.__table__ = _t.tometadata(db.metadata)
    except Exception:
        # best-effort remap; don't crash app startup
        pass
    # isort: on

    migrate.init_app(flask_app, db)
    migrate_examination.init_app(
        flask_app,
        db,
        directory="migrations_examination",
        compare_type=True,
        render_as_batch=True,
    )

    mail.init_app(flask_app)
    csrf.init_app(flask_app)
    login_manager.init_app(flask_app)
    login_manager.login_view = "auth.login"

    from .paths import case_root, investigation_root  # noqa: WPS433

    with flask_app.app_context():
        _ = case_root()
        _ = investigation_root()

    from .models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .investigations import investigations_bp
    from .routes import main_bp
    from .views.auth import auth_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(investigations_bp, url_prefix="/investigations")

    from app.error_handlers import register_error_handlers

    register_error_handlers(flask_app)

    @flask_app.errorhandler(RequestEntityTooLarge)
    def _too_large(e):  # noqa: ARG001
        return "File too large", 413

    _checked_tables = False

    @flask_app.before_request
    def check_essential_tables_once():
        nonlocal _checked_tables
        if (
            _checked_tables
            or flask_app.config.get("TESTING")
            or flask_app.config.get("ENV") != "production"
        ):
            return
        from sqlalchemy import inspect

        required_tables = ["user", "case", "change_log", "uploaded_file"]
        inspector = inspect(db.engine)
        missing = [t for t in required_tables if not inspector.has_table(t)]
        if missing:
            raise RuntimeError(f"Missing tables: {missing}")
        _checked_tables = True

    @flask_app.route("/healthz")
    def healthz():
        return "ok", 200

    from .investigations.routes import (  # noqa: WPS433
        list_investigations as _list_investigations,
    )

    flask_app.add_url_rule(
        "/",
        endpoint="investigations.list_investigations",
        view_func=_list_investigations,
    )

    flask_app.jinja_env.filters["datetimeformat"] = lambda value: (
        value.strftime("%Y-%m-%dT%H:%M") if value else ""
    )
    flask_app.jinja_env.filters["getattr"] = lambda obj, name: getattr(obj, name, "")

    def localtime(value: datetime | None):
        if not value:
            return ""
        if value.tzinfo is None:
            value = value.replace(tzinfo=BUDAPEST_TZ)
        return value.astimezone(BUDAPEST_TZ).strftime("%Y-%m-%d %H:%M")

    flask_app.jinja_env.filters["localtime"] = localtime

    def local_dt(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M"):
        if not value:
            return ""
        if getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=BUDAPEST_TZ)
        return value.astimezone(BUDAPEST_TZ).strftime(fmt)

    def iso_dt(value: datetime | None):
        if not value:
            return ""
        if getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=BUDAPEST_TZ)
        return value.astimezone(BUDAPEST_TZ).isoformat()

    flask_app.jinja_env.filters["local_dt"] = local_dt
    flask_app.jinja_env.filters["iso_dt"] = iso_dt
    flask_app.jinja_env.filters["fmt_date"] = fmt_date
    flask_app.jinja_env.globals["fmt_date"] = fmt_date
    flask_app.jinja_env.globals["BUDAPEST_TZ"] = BUDAPEST_TZ

    def _datetime_local(val):
        if not val:
            return ""
        try:
            dt = val
            try:
                if dt.tzinfo is None:
                    dt = BUDAPEST_TZ.localize(dt)
                dt = dt.astimezone(BUDAPEST_TZ)
            except Exception:  # pragma: no cover - best effort
                pass
            return dt.strftime("%Y-%m-%dT%H:%M")
        except Exception:  # pragma: no cover - best effort
            return ""

    flask_app.jinja_env.filters["datetime_local"] = _datetime_local

    TOX_ORDER_RE = re.compile(
        r"^(?P<name>.+?) rendelve: (?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) [\u2013-] (?P<user>.+)$"
    )

    def parse_tox_changelog(value: str | None):
        if not value:
            return None
        m = TOX_ORDER_RE.match(value.strip())
        if not m:
            return None
        return {"name": m.group("name"), "ts": m.group("ts"), "user": m.group("user")}

    flask_app.jinja_env.filters["parse_tox_changelog"] = parse_tox_changelog

    NOTE_RE = re.compile(
        r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) [\u2013-] (?P<user>[^\]]+)\]\s*(?P<text>.*)$"
    )

    def parse_note_changelog(value: str | None):
        if not value:
            return None
        m = NOTE_RE.match(value.strip())
        if not m:
            return None
        return {"ts": m.group("ts"), "user": m.group("user"), "text": m.group("text")}

    flask_app.jinja_env.filters["parse_note_changelog"] = parse_note_changelog

    @flask_app.after_request
    def add_no_store_headers(response):
        if flask_app.config.get("NO_STORE_HEADERS_ENABLED", True):
            ep = request.endpoint or ""
            if not (ep.startswith("static") or request.path.startswith("/static/")):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0, private"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

        # ✅ Relaxed CSP (allows Bootstrap/Fonts CDNs)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;",
        )
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if flask_app.config.get(
            "PREFERRED_URL_SCHEME", ""
        ).lower() == "https" or flask_app.config.get("ENABLE_HSTS", False):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=15552000; includeSubDomains"
            )
        return response

    if (
        not flask_app.debug
        and not flask_app.testing
        and not os.getenv("DISABLE_FILE_LOGGING")
    ):
        log_dir = os.path.join(flask_app.instance_path, "logs")
        os.makedirs(log_dir, exist_ok=True)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        try:
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, "app.log"),
                maxBytes=10240,
                backupCount=10,
                delay=True,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            flask_app.logger.addHandler(file_handler)
        except PermissionError:
            stream = logging.StreamHandler()
            stream.setLevel(logging.INFO)
            stream.setFormatter(formatter)
            flask_app.logger.addHandler(stream)

        flask_app.logger.setLevel(logging.INFO)
        flask_app.logger.info("Logging initialized.")

    return flask_app
