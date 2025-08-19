# scripts/reset_storage_and_data_2.py
import os
import shutil
import argparse
from sqlalchemy import text

from app import create_app, db
from app.models import Case, UploadedFile, ChangeLog, TaskMessage
# Optional models
try:
    from app.models import EmailNotification
except Exception:
    EmailNotification = None
try:
    from app.models import CaseSheetField
except Exception:
    CaseSheetField = None

from app.investigations.models import (
    Investigation,
    InvestigationAttachment,
    InvestigationNote,
    InvestigationChangeLog,
)
from app.paths import case_root, investigation_root

# Preserve rules
PRESERVE_DIR_NAMES = {"autofill-word-do-not-edit", "webfill-do-not-edit"}
PRESERVE_SUFFIXES = ("-do-not-edit",)

def _is_preserved_dirname(name: str) -> bool:
    return (name in PRESERVE_DIR_NAMES) or any(name.endswith(sfx) for sfx in PRESERVE_SUFFIXES)

def _clear_dir_preserving(root_path: str, dry_run: bool = False):
    """
    Remove everything under root_path EXCEPT any directories whose *basename*
    should be preserved. If root_path does not exist, create it (unless dry_run).
    """
    try:
        if not dry_run:
            os.makedirs(root_path, exist_ok=True)
        if not os.path.exists(root_path):
            print(f"[INFO] (dry-run) Would create: {root_path}")
            return

        for current_root, dirnames, filenames in os.walk(root_path, topdown=True):
            base = os.path.basename(current_root)

            # If the current directory itself is preserved, don't descend
            if _is_preserved_dirname(base):
                dirnames[:] = []
                continue

            # Prune preserved subdirs from traversal
            dirnames[:] = [d for d in dirnames if not _is_preserved_dirname(d)]

            # Delete files in current directory
            for fname in filenames:
                fpath = os.path.join(current_root, fname)
                if dry_run:
                    print(f"[INFO] (dry-run) Would remove file: {fpath}")
                else:
                    try:
                        os.remove(fpath)
                    except Exception as e:
                        print(f"[WARN] Could not remove file {fpath}: {e}")

            # Delete any non-preserved subdirectories
            for d in os.listdir(current_root):
                if _is_preserved_dirname(d):
                    continue
                dpath = os.path.join(current_root, d)
                if os.path.isdir(dpath):
                    if dry_run:
                        print(f"[INFO] (dry-run) Would remove folder: {dpath}")
                    else:
                        try:
                            shutil.rmtree(dpath)
                        except Exception as e:
                            print(f"[WARN] Could not remove folder {dpath}: {e}")

    except Exception as e:
        print(f"[WARN] Could not reset folder {root_path}: {e}")

def _delete_all(model, label: str, dry_run: bool = False):
    count = model.query.count()
    if dry_run:
        print(f"[INFO] (dry-run) Would delete {count} rows from {label}")
        return 0
    deleted = model.query.delete(synchronize_session=False)
    print(f"[INFO] Deleted {deleted} rows from {label}")
    return deleted

def _maybe_delete(model, label: str, dry_run: bool = False):
    if model is None:
        print(f"[INFO] {label} not present in this build — skipping.")
        return 0
    return _delete_all(model, label, dry_run=dry_run)

def _vacuum_sqlite(bind_name, dry_run: bool = False):
    try:
        engine = db.get_engine(bind=bind_name)
        which = bind_name or "default"
        if dry_run:
            print(f"[INFO] (dry-run) Would VACUUM SQLite database ({which})")
            return
        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM"))
        print(f"[INFO] VACUUM completed for SQLite database ({which})")
    except Exception as e:
        which = bind_name or "default"
        print(f"[WARN] VACUUM failed for ({which}): {e}")

def parse_args():
    p = argparse.ArgumentParser(
        description="Factory reset: wipe all case/investigation data and uploads, preserve users and template dirs."
    )
    p.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    p.add_argument("--yes", action="store_true", help="Skip interactive prompt. USE WITH CAUTION.")
    p.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM on SQLite databases after deletion.")
    return p.parse_args()

def main():
    args = parse_args()

    if not args.yes and not args.dry_run:
        print("⚠️  This will permanently delete ALL case/investigation data and uploaded files,")
        print("   preserving only users and any directories named:", ", ".join(sorted(PRESERVE_DIR_NAMES)))
        confirm = input('Type YES to confirm factory reset: ')
        if confirm.strip() != "YES":
            print("Aborted.")
            return

    app = create_app()
    with app.app_context():
        # Canonical roots from app.paths
        cases_root = case_root()
        inv_root = investigation_root()

        # Live folders under app root (as you specified)
        legacy_cases_root = os.path.join(app.root_path, "uploads_boncolasok")
        legacy_invest_root = os.path.join(app.root_path, "uploads_vizsgalatok")

        mode = "(dry-run) " if args.dry_run else ""
        print(f"[INFO] {mode}Resetting storage (preserving {sorted(PRESERVE_DIR_NAMES)}):")
        print(f"  Cases (canonical):          {cases_root}")
        print(f"  Investigations (canonical): {inv_root}")
        print(f"  Cases (live):               {legacy_cases_root}")
        print(f"  Investigations (live):      {legacy_invest_root}")

        # Purge canonical roots
        _clear_dir_preserving(cases_root, dry_run=args.dry_run)
        _clear_dir_preserving(inv_root,  dry_run=args.dry_run)

        # Purge live folders
        if os.path.exists(legacy_cases_root):
            _clear_dir_preserving(legacy_cases_root, dry_run=args.dry_run)
        else:
            print(f"[INFO] {mode}Live cases folder missing (ok): {legacy_cases_root}")

        if os.path.exists(legacy_invest_root):
            _clear_dir_preserving(legacy_invest_root, dry_run=args.dry_run)
        else:
            print(f"[INFO] {mode}Live investigations folder missing (ok): {legacy_invest_root}")

        print(f"[INFO] {mode}Deleting investigation-related rows (examination bind)...")
        _delete_all(InvestigationAttachment, "examination.InvestigationAttachment", dry_run=args.dry_run)
        _delete_all(InvestigationNote,       "examination.InvestigationNote",       dry_run=args.dry_run)
        _delete_all(InvestigationChangeLog,  "examination.InvestigationChangeLog",  dry_run=args.dry_run)
        _delete_all(Investigation,           "examination.Investigation",           dry_run=args.dry_run)

        print(f"[INFO] {mode}Deleting case-related rows (default bind)...")
        _delete_all(UploadedFile,        "default.UploadedFile",      dry_run=args.dry_run)
        _delete_all(TaskMessage,         "default.TaskMessage",       dry_run=args.dry_run)
        _delete_all(ChangeLog,           "default.ChangeLog",         dry_run=args.dry_run)
        _maybe_delete(EmailNotification, "default.EmailNotification", dry_run=args.dry_run)
        _maybe_delete(CaseSheetField,    "default.CaseSheetField",    dry_run=args.dry_run)
        _delete_all(Case,                "default.Case",              dry_run=args.dry_run)

        if args.dry_run:
            print("[INFO] (dry-run) Preserved dir names:", sorted(PRESERVE_DIR_NAMES))
            print("[DONE] (dry-run) No changes committed. Users preserved; template dirs would be kept.")
            return

        db.session.commit()
        print("[INFO] Changes committed to databases.")

        if not args.no_vacuum:
            _vacuum_sqlite(bind_name=None,          dry_run=False)
            _vacuum_sqlite(bind_name="examination", dry_run=False)

        print("[DONE] Storage cleared and tables wiped (users preserved; template dirs kept).")

if __name__ == "__main__":
    # Usage (Windows, repo root, venv):
    #   python -m scripts.reset_storage_and_data_2 --dry-run
    #   python -m scripts.reset_storage_and_data_2 --yes
    main()
