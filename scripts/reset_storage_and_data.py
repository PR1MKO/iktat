"""Guarded storage/data reset utility.

Default behaviour is a dry-run that reports the actions without touching
anything. Deletions are only executed when *both* confirmation flags are
provided and the environment variable ``ALLOW_INSTANCE_DELETION`` is set to
``"1"``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from app import create_app, db
from app.investigations.models import (
    Investigation,
    InvestigationAttachment,
    InvestigationChangeLog,
    InvestigationNote,
)
from app.models import Case, ChangeLog, TaskMessage, UploadedFile
from app.paths import case_root, investigation_root


def _is_production() -> bool:
    return (
        os.getenv("FLASK_ENV") == "production" or os.getenv("APP_ENV") == "production"
    )


def _ensure_instance_path(path: Path) -> None:
    if "instance" not in path.resolve().parts:
        print(f"Refusing to touch non-instance path: {path}", file=sys.stderr)
        raise SystemExit(3)


def _delete_model(model, label: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would delete all rows from {label}")
        return
    deleted = model.query.delete(synchronize_session=False)
    print(f"[INFO] Deleted {deleted} rows from {label}")


def _reset_directory(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would remove directory tree: {path}")
        return

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    keep = path / ".keep"
    if not keep.exists():
        keep.touch()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DANGEROUS: wipes storage roots and related database tables. Guarded by default."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Perform deletion (requires --i-know-what-im-doing and ALLOW_INSTANCE_DELETION=1)",
    )
    parser.add_argument(
        "--i-know-what-im-doing",
        action="store_true",
        help="Additional confirmation flag to acknowledge destructive behaviour.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run mode (default unless all confirmations are present).",
    )
    args = parser.parse_args(argv)

    if _is_production():
        print("Refusing to run in production.", file=sys.stderr)
        return 2

    confirmations = (
        args.force
        and args.i_know_what_im_doing
        and os.getenv("ALLOW_INSTANCE_DELETION") == "1"
    )
    dry_run = args.dry_run or not confirmations
    if dry_run and not args.dry_run:
        print("[SAFE] Missing confirmations. Running in DRY-RUN mode.", file=sys.stderr)

    app = create_app()
    with app.app_context():
        roots = [Path(case_root()), Path(investigation_root())]
        for root in roots:
            _ensure_instance_path(root)

        mode = "(dry-run) " if dry_run else ""
        print(
            f"[INFO] {mode}Resetting storage:\n  Cases: {roots[0]}\n  Investigations: {roots[1]}"
        )

        for root in roots:
            _reset_directory(root, dry_run=dry_run)

        print(f"[INFO] {mode}Deleting investigation-related rows (examination bind)...")
        _delete_model(
            InvestigationAttachment,
            "examination.InvestigationAttachment",
            dry_run=dry_run,
        )
        _delete_model(
            InvestigationNote,
            "examination.InvestigationNote",
            dry_run=dry_run,
        )
        _delete_model(
            InvestigationChangeLog,
            "examination.InvestigationChangeLog",
            dry_run=dry_run,
        )
        _delete_model(
            Investigation,
            "examination.Investigation",
            dry_run=dry_run,
        )

        print(f"[INFO] {mode}Deleting case-related rows (default bind)...")
        _delete_model(UploadedFile, "default.UploadedFile", dry_run=dry_run)
        _delete_model(TaskMessage, "default.TaskMessage", dry_run=dry_run)
        _delete_model(ChangeLog, "default.ChangeLog", dry_run=dry_run)
        _delete_model(Case, "default.Case", dry_run=dry_run)

        if dry_run:
            print("[DONE] (dry-run) No changes committed. Users preserved.")
            return 0

        db.session.commit()
        print("[DONE] Storage cleared and tables wiped (users preserved).")

    return 0


if __name__ == "__main__":  # pragma: no cover - invoked via CLI
    sys.exit(main())
