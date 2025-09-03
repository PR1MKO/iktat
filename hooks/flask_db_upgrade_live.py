# Live temp-DB upgrade for SQLite (works with render_as_batch and multi-dir)
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_APP", "app:create_app")

from flask_migrate import upgrade as fm_upgrade  # noqa: E402

from app import create_app  # noqa: E402


def _uri_to_path(uri: str) -> str:
    """Return filesystem path for sqlite:/// URIs, else ''."""
    if not uri or not uri.startswith("sqlite:///"):
        return ""
    return uri.replace("sqlite:///", "", 1)


def _copy_if_exists(src_path: str) -> str:
    """Copy src sqlite db to a NamedTemporaryFile; return temp path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    if src_path and os.path.exists(src_path):
        shutil.copy2(src_path, tmp.name)
    return tmp.name


def main() -> int:
    # 1) Create a *real* app to discover the current URIs
    discovery_app = create_app()
    with discovery_app.app_context():
        main_uri = discovery_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        binds = dict(discovery_app.config.get("SQLALCHEMY_BINDS") or {})
        exam_uri = binds.get("examination", "")

    # 2) Only meaningful for SQLite
    if not (
        main_uri.startswith("sqlite:///")
        or (exam_uri and exam_uri.startswith("sqlite:///"))
    ):
        print("Skip: live temp upgrade is only implemented for SQLite.")
        return 0

    # 3) Make temp copies
    main_src = _uri_to_path(main_uri)
    exam_src = _uri_to_path(exam_uri) if exam_uri else ""

    tmp_main = _copy_if_exists(main_src) if main_uri else ""
    tmp_exam = _copy_if_exists(exam_src) if exam_src else ""

    # 4) Build a *fresh* app configured to use the temp copies
    test_config = {}
    if main_uri:
        test_config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmp_main}"
    if exam_uri:
        test_config["SQLALCHEMY_BINDS"] = {"examination": f"sqlite:///{tmp_exam}"}

    flask_app = create_app(test_config=test_config)

    try:
        with flask_app.app_context():
            # 5) Upgrade default tree
            fm_upgrade()  # defaults to "migrations"

            # 6) Upgrade examination tree
            if exam_uri:
                fm_upgrade(directory="migrations_examination")

        print("Alembic Live Upgrade (temp SQLite) OK")
        return 0
    except Exception as e:
        print(f"Alembic Live Upgrade FAILED: {e}")
        return 1
    finally:
        for p in (tmp_main, tmp_exam):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
