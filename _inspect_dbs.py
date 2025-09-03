import os
import pathlib
import sqlite3
import sys

from app import create_app


def list_objs(db_path: pathlib.Path):
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT type,name FROM sqlite_master WHERE type IN ('table','index') ORDER BY name"
    ).fetchall()
    con.close()
    return rows


app = create_app()
with app.app_context():
    inst = pathlib.Path(app.instance_path)
    main = inst / ("test.db" if app.config.get("TESTING") else "forensic_cases.db")

    # compute exam path exactly like app/__init__.py
    exam_name = "test_examination.db" if app.config.get("TESTING") else "examination.db"
    exam_default = f"sqlite:///{inst / exam_name}"
    exam_url = os.getenv("EXAMINATION_DATABASE_URL", exam_default)

    exam_path = None
    if exam_url.startswith("sqlite:///"):
        exam_path = pathlib.Path(exam_url.replace("sqlite:///", ""))

    print("MAIN DB:", main)
    main_rows = list_objs(main)
    main_hits = [(t, n) for t, n in main_rows if "investigation" in n]
    for t, n in main_hits:
        print("  ", t, n)
    if not main_hits:
        print("  (no 'investigation*' objects)")

    if exam_path:
        print("EXAM DB:", exam_path)
        exam_rows = list_objs(exam_path)
        exam_hits = [(t, n) for t, n in exam_rows if "investigation" in n]
        for t, n in exam_hits:
            print("  ", t, n)
        if not exam_hits:
            print("  (no 'investigation*' objects)")

    # exit code 0 if MAIN is clean, 2 if MAIN still has stray investigation*
    if main_hits:
        sys.exit(2)
    sys.exit(0)
