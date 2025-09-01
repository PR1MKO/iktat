# Live temp-DB upgrade for SQLite (works with batch_alter_table; replaces --sql dry-run)
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_APP", "app:create_app")

from flask_migrate import upgrade  # noqa: E402

# Import app factory safely after adjusting sys.path
from app import create_app  # noqa: E402


def _uri_to_path(uri: str) -> str:
    if not uri or not uri.startswith("sqlite:///"):
        return ""
    return uri.replace("sqlite:///", "", 1)


def main() -> int:
    app = create_app()
    with app.app_context():
        main_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        binds = dict(app.config.get("SQLALCHEMY_BINDS", {}))

        # Only meaningful for SQLite
        if not main_uri.startswith("sqlite:///"):
            print("Skip: non-SQLite dialect.")
            return 0

        main_src = _uri_to_path(main_uri)
        exam_uri = binds.get("examination", "")
        exam_src = _uri_to_path(exam_uri) if exam_uri else ""

        # Prepare temp copies
        tmp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp_main.close()
        if main_src and os.path.exists(main_src):
            shutil.copy2(main_src, tmp_main.name)

        tmp_exam = None
        if exam_src:
            tmp_exam = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
            tmp_exam.close()
            if os.path.exists(exam_src):
                shutil.copy2(exam_src, tmp_exam.name)

        # Point config to temp DBs
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmp_main.name}"
        if tmp_exam:
            binds["examination"] = f"sqlite:///{tmp_exam.name}"
            app.config["SQLALCHEMY_BINDS"] = binds

        try:
            upgrade()  # real upgrade on temp DBs
            print("Alembic Live Upgrade (temp SQLite) OK")
            return 0
        except Exception as e:
            print(f"Alembic Live Upgrade FAILED: {e}")
            return 1
        finally:
            for p in [tmp_main.name, tmp_exam.name if tmp_exam else None]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass


if __name__ == "__main__":
    raise SystemExit(main())
