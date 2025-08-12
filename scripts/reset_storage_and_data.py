# scripts/reset_storage_and_data.py
import os
import shutil

from app import create_app, db
from app.models import Case, UploadedFile, ChangeLog, TaskMessage  # default bind
from app.investigations.models import (
    Investigation,
    InvestigationAttachment,
    InvestigationNote,
    InvestigationChangeLog,
)  # examination bind

def _safe_rmtree(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"[WARN] Could not reset folder {path}: {e}")

def main():
    app = create_app()
    with app.app_context():
        # Folders from config
        cases_root = app.config.get("UPLOAD_FOLDER")
        inv_root = app.config.get("INVESTIGATION_UPLOAD_FOLDER")

        print(f"[INFO] Resetting storage:\n  Cases: {cases_root}\n  Investigations: {inv_root}")
        _safe_rmtree(cases_root)
        _safe_rmtree(inv_root)

        print("[INFO] Deleting investigation-related rows (examination bind)...")
        # Delete children first
        InvestigationAttachment.query.delete()  # bind: examination
        InvestigationNote.query.delete()
        InvestigationChangeLog.query.delete()
        Investigation.query.delete()

        print("[INFO] Deleting case-related rows (default bind)...")
        UploadedFile.query.delete()
        TaskMessage.query.delete()
        ChangeLog.query.delete()
        Case.query.delete()

        # DO NOT touch the users table

        db.session.commit()
        print("[DONE] Storage cleared and tables wiped (users preserved).")

if __name__ == "__main__":
    # This script is meant to be run manually (e.g., `python scripts/reset_storage_and_data.py`)
    main()