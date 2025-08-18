"""Migration script to convert case numbers from YYYY-NNN to NNNN-YYYY format.

Steps:
    - Update Case.case_number values
    - Rename upload folders and key files
    - Replace occurrences in AuditLog.details and TaskMessage.message

Usage:
    python scripts/migrate_case_number_format.py
"""
import os
import re
from app import create_app, db
from app.models import Case, AuditLog, TaskMessage
from app.paths import case_root, case_folder_name

OLD_RE = re.compile(r"^(\d{4})-(\d{3})$")
LOG_RE = re.compile(r"\b(\d{4})-(\d{3})\b")

app = create_app()


def rename_files(base_dir: str, old: str, new: str) -> None:
    """Rename case folder and known files from old to new numbering."""
    old_dir = os.path.join(base_dir, case_folder_name(old))
    new_dir = os.path.join(base_dir, case_folder_name(new))
    if os.path.exists(old_dir):
        os.rename(old_dir, new_dir)
        mappings = [
            (
                f"halottvizsgalati_bizonyitvany-{old}.txt",
                f"halottvizsgalati_bizonyitvany-{new}.txt",
            ),
            (
                f"Toxikológiai-kirendelő-{old}.docx",
                f"Toxikológiai-kirendelő-{new}.docx",
            ),
            (
                f"changelog_{old}.csv",
                f"changelog_{new}.csv",
            ),
        ]
        for src_name, dst_name in mappings:
            src = os.path.join(new_dir, src_name)
            dst = os.path.join(new_dir, dst_name)
            if os.path.exists(src):
                os.rename(src, dst)


with app.app_context():
    upload_root = str(case_root())
    cases = Case.query.all()
    for case in cases:
        m = OLD_RE.match(case.case_number)
        if not m:
            continue
        year, seq = m.groups()
        new_num = f"{int(seq):04d}-{year}"
        old_num = case.case_number
        if old_num == new_num:
            continue
        case.case_number = new_num
        rename_files(upload_root, old_num, new_num)
    # Update textual references in AuditLog and TaskMessage
    logs = AuditLog.query.all()
    for log in logs:
        if not log.details:
            continue
        new_details = LOG_RE.sub(lambda m: f"{int(m.group(2)):04d}-{m.group(1)}", log.details)
        if new_details != log.details:
            log.details = new_details
    msgs = TaskMessage.query.all()
    for msg in msgs:
        new_msg = LOG_RE.sub(lambda m: f"{int(m.group(2)):04d}-{m.group(1)}", msg.message)
        if new_msg != msg.message:
            msg.message = new_msg
    db.session.commit()
    print(f"Processed {len(cases)} cases.")