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
from app.paths import case_root, investigation_root

PRESERVE_DIR_NAMES = {"autofill-word-do-not-edit"}

def _clear_dir_preserving(root_path: str, preserve_names=PRESERVE_DIR_NAMES):
    """
    Remove everything under root_path EXCEPT any directories whose *basename*
    is listed in preserve_names. Those directories (and their contents) remain intact.
    If root_path does not exist, it will be created.
    """
    try:
        os.makedirs(root_path, exist_ok=True)
        # Walk top-down so we can prune preserved dirs
        for current_root, dirnames, filenames in os.walk(root_path, topdown=True):
            # If this directory itself is a preserved one, skip deleting inside it
            if os.path.basename(current_root) in preserve_names:
                # Do not descend further into preserved dirs
                dirnames[:] = []
                continue

            # Prune preserved dirs from traversal (so nothing inside them is touched)
            dirnames[:] = [d for d in dirnames if d not in preserve_names]

            # Delete files in the current directory
            for fname in filenames:
                fpath = os.path.join(current_root, fname)
                try:
                    os.remove(fpath)
                except Exception as e:
                    print(f"[WARN] Could not remove file {fpath}: {e}")

            # After files are gone, delete any non-preserved subdirs we pruned earlier
            # (we need a second pass because we removed them from dirnames to avoid descending)
            for d in os.listdir(current_root):
                if d in preserve_names:
                    continue
                dpath = os.path.join(current_root, d)
                if os.path.isdir(dpath):
                    try:
                        shutil.rmtree(dpath)
                    except Exception as e:
                        print(f"[WARN] Could not remove folder {dpath}: {e}")

    except Exception as e:
        print(f"[WARN] Could not reset folder {root_path}: {e}")

def main():
    app = create_app()
    with app.app_context():
        # Folders from config
        cases_root = case_root()
        inv_root = investigation_root()

        print(f"[INFO] Resetting storage (preserving {PRESERVE_DIR_NAMES}):")
        print(f"  Cases: {cases_root}")
        print(f"  Investigations: {inv_root}")

        _clear_dir_preserving(cases_root)  # nothing preserved here unless such a folder exists
        _clear_dir_preserving(inv_root)    # keeps any 'autofill-word-do-not-edit' dirs intact

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
        print("[DONE] Storage cleared and tables wiped (users preserved; template dirs kept).")

if __name__ == "__main__":
    # This script is meant to be run manually (e.g., `python scripts/reset_storage_and_data.py`)
    main()
