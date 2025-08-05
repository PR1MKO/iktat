"""
Task: Wipe all cases and their folders. Keep users, roles, and logic untouched.

Requirements:
- Delete all records from the Case table
- Also delete related entries in ChangeLog, UploadedFile, TaskMessage
- Remove all folders under: app/uploads/
- Do NOT delete the uploads folder itself
"""

from app import create_app, db
from app.models import Case, ChangeLog, UploadedFile, TaskMessage
import os
import shutil

app = create_app()

with app.app_context():
    cases = Case.query.all()
    for case in cases:
        ChangeLog.query.filter_by(case_id=case.id).delete()
        UploadedFile.query.filter_by(case_id=case.id).delete()
        TaskMessage.query.filter_by(case_id=case.id).delete()
        db.session.delete(case)
    db.session.commit()
    print(f"✅ Deleted {len(cases)} cases from database.")

    # Delete all subfolders under app/uploads/
    upload_root = os.path.join(app.root_path, "uploads")
    if os.path.exists(upload_root):
        deleted = 0
        for item in os.listdir(upload_root):
            full_path = os.path.join(upload_root, item)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
                deleted += 1
        print(f"✅ Removed {deleted} case folders from: {upload_root}")
    else:
        print(f"⚠️ Upload folder not found at: {upload_root}")
