import pathlib
import shutil
import sqlite3

from app import create_app
from app.utils.time_utils import now_utc

EXAM_TABLES_ORDERED = (
    "investigation_attachment",
    "investigation_note",
    "investigation_change_log",
    "investigation",
)

app = create_app()
with app.app_context():
    inst = pathlib.Path(app.instance_path)
    main = inst / ("test.db" if app.config.get("TESTING") else "forensic_cases.db")
    exam = inst / (
        "test_examination.db" if app.config.get("TESTING") else "examination.db"
    )

    ts = now_utc().strftime("%Y%m%d-%H%M%S")
    for p in (main, exam):
        if p.exists():
            dst = p.with_name(f"{p.stem}.bak.{ts}{p.suffix}")
            shutil.copy2(p, dst)
            print("Backed up:", p, "->", dst)

    if not main.exists():
        print("Main DB not found:", main)
        raise SystemExit(0)

    con = sqlite3.connect(str(main))
    cur = con.cursor()

    # drop indexes that reference investigation*
    idxs = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%investigation%'"
    ).fetchall()
    for (name,) in idxs:
        print("DROP INDEX IF EXISTS", name)
        cur.execute(f'DROP INDEX IF EXISTS "{name}"')

    # drop tables (child -> parent)
    for tbl in EXAM_TABLES_ORDERED:
        exists = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,)
        ).fetchone()
        if exists:
            print("DROP TABLE IF EXISTS", tbl)
            cur.execute(f'DROP TABLE IF EXISTS "{tbl}"')

    con.commit()
    con.close()
    print("Purge complete.")
