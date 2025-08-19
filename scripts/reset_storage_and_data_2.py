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

# Preserve rules for *legacy/live* app roots ONLY
PRESERVE_DIR_NAMES = {"autofill-word-do-not-edit", "webfill-do-not-edit"}
PRESERVE_SUFFIXES = ("-do-not-edit",)

def _is_preserved(name: str, preserve_names, preserve_suffixes) -> bool:
    return (name in preserve_names) or any(name.endswith(sfx) for sfx in preserve_suffixes)

def _clear_dir_preserving(
    root_path: str,
    dry_run: bool = False,
    preserve_names=PRESERVE_DIR_NAMES,
    preserve_suffixes=PRESERVE_SUFFIXES,
):
    """
    Remove everything under root_path EXCEPT any directories whose *basename*
    matches the provided preserve rules. To nuke everything, pass empty sets/tuples
    for preserve_names and preserve_suffixes.
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
            if _is_preserved(base, preserve_names, preserve_suffixes):
                dirnames[:] = []
                continue

            # Prune preserved subdirs from traversal
            dirnames[:] = [
                d for d in dirnames
                if not _is_preserved(d, preserve_names, preserve_suffixes)
            ]

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
                if _is_preserved(d, preserve_names, preserve_suffixes):
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
        description=(
            "Factory reset: wipe all case/investigation data and uploads. "
            "Instance roots are wiped with NO preservation. "
            "Legacy app roots preserve *-do-not-edit directories."
        )
    )
    p.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting.")
    p.add_argument("--yes", action="store_true", help="Skip interactive prompt. USE WITH CAUTION.")
    p.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM on SQLite databases after deletion.")
    return p.parse_args()

def main():
    args = parse_args()

    if not args.yes and not args.dry_run:
        print("⚠️  This will permanently delete ALL case/investigation data and uploaded files.")
        print("   Instance roots will be wiped with NO preserved directories.")
        print("   Legacy app roots will preserve:", ", ".join(sorted(PRESERVE_DIR_NAMES)))
        confirm = input('Type YES to confirm factory reset: ')
        if confirm.strip() != "YES":
            print("Aborted.")
            return

    app = create_app()
    with app.app_context():
        # Canonical instance roots (WIPE EVERYTHING here)
        cases_root = case_root()               # instance\uploads_cases
        inv_root = investigation_root()        # instance\uploads_investigations

        # Legacy/live app roots (preserve *-do-not-edit)
        legacy_cases_root = os.path.join(app.root_path, "uploads_boncolasok")
        legacy_invest_root = os.path.join(app.root_path, "uploads_vizsgalatok")

        mode = "(dry-run) " if args.dry_run else ""
        print(f"[INFO] {mode}Resetting storage...")
        print(f"  Instance cases (NO preserve):          {cases_root}")
        print(f"  Instance investigations (NO preserve): {inv_root}")
        print(f"  App cases (preserve do-not-edit):      {legacy_cases_root}")
        print(f"  App investigations (preserve):         {legacy_invest_root}")

        # Purge instance roots with NO preservation at all
        _clear_dir_preserving(
            cases_root,
            dry_run=args.dry_run,
            preserve_names=set(),
            preserve_suffixes=(),
        )
        _clear_dir_preserving(
            inv_root,
            dry_run=args.dry_run,
            preserve_names=set(),
            preserve_suffixes=(),
        )

        # Purge legacy/live app roots WITH preservation of do-not-edit dirs
        if os.path.exists(legacy_cases_root):
            _clear_dir_preserving(
                legacy_cases_root,
                dry_run=args.dry_run,
                preserve_names=PRESERVE_DIR_NAMES,
                preserve_suffixes=PRESERVE_SUFFIXES,
            )
        else:
            print(f"[INFO] {mode}Legacy cases folder missing (ok): {legacy_cases_root}")

        if os.path.exists(legacy_invest_root):
            _clear_dir_preserving(
                legacy_invest_root,
                dry_run=args.dry_run,
                preserve_names=PRESERVE_DIR_NAMES,
                preserve_suffixes=PRESERVE_SUFFIXES,
            )
        else:
            print(f"[INFO] {mode}Legacy investigations folder missing (ok): {legacy_invest_root}")

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
            print("[INFO] (dry-run) Instance roots: wiped with NO preservation.")
            print("[INFO] (dry-run) App roots preserved dir names:", sorted(PRESERVE_DIR_NAMES))
            print("[DONE] (dry-run) No changes committed. Users preserved.")
            return

        db.session.commit()
        print("[INFO] Changes committed to databases.")

        if not args.no_vacuum:
            _vacuum_sqlite(bind_name=None,          dry_run=False)
            _vacuum_sqlite(bind_name="examination", dry_run=False)

        print("[DONE] Storage cleared and tables wiped (users preserved).")
        print("[NOTE] Instance roots were fully cleared; re-seed do-not-edit templates from the safe source.")

if __name__ == "__main__":
    # Usage (Windows, repo root, venv):
    #   python -m scripts.reset_storage_and_data_2 --dry-run
    #   python -m scripts.reset_storage_and_data_2 --yes
    main()
