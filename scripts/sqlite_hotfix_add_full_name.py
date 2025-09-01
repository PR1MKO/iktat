# scripts/sqlite_hotfix_add_full_name.py
from sqlalchemy import text

from app import create_app, db

app = create_app()
with app.app_context():
    # SQLite ALTER TABLE ADD COLUMN is safe (no data loss) and idempotent enough for our need
    try:
        db.session.execute(text("ALTER TABLE user ADD COLUMN full_name VARCHAR(128)"))
        db.session.commit()
        print("[OK] Added user.full_name")
    except Exception as e:
        # If it already exists or any other issue, print it so we can see what's up
        print("[WARN] Could not add column (maybe already exists?):", e)
