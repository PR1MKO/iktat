#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as a script
sys.path.append(str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(
        description="Verify examination uploads vs DB attachments (read-only)."
    )
    parser.add_argument(
        "--case", required=True, help="Investigation case number, e.g. 'V:0002/2025'"
    )
    args = parser.parse_args()

    # Lazy import app to avoid heavy startup before args parse
    from app import create_app, db
    from app.investigations.models import Investigation
    from app.paths import investigation_expected_folder

    app = create_app()
    with app.app_context():
        inv = db.session.query(Investigation).filter_by(case_number=args.case).first()
        if not inv:
            print(f"[ERROR] Investigation not found for case_number={args.case}")
            return 2

        # Fetch attachments for this investigation
        from app.investigations.models import InvestigationAttachment

        atts = (
            db.session.query(InvestigationAttachment)
            .filter_by(investigation_id=inv.id)
            .order_by(InvestigationAttachment.id.asc())
            .all()
        )

        folder = investigation_expected_folder(inv.case_number)
        missing = []
        present = []
        for a in atts:
            fpath = Path(folder) / a.filename
            (present if fpath.exists() else missing).append(a.filename)

        print("=== Examination Upload Verification ===")
        print(f"Case number : {inv.case_number}")
        print(f"DB id       : {inv.id}")
        print(f"Folder      : {folder}")
        print(f"Attachments : {len(atts)}")
        print(f"Present     : {present}")
        print(f"Missing     : {missing}")

        # Exit code semantics
        if missing:
            print(f"[FAIL] {len(missing)} attachment(s) missing on disk.")
            return 1
        else:
            print("[OK] All DB attachments are present on disk.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
