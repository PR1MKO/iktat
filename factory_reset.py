from app import create_app, db
from app.models import Case, ChangeLog, UploadedFile
import os
import shutil

app = create_app()

if app.config.get('ENV') == 'production' and not app.config.get('TESTING'):
    raise RuntimeError('Factory reset blocked in production environment')

with app.app_context():
    cases_deleted = db.session.query(Case).delete(synchronize_session=False)
    changelog_deleted = db.session.query(ChangeLog).delete(synchronize_session=False)
    uploaded_deleted = db.session.query(UploadedFile).delete(synchronize_session=False)
    db.session.commit()

    print(f"\u2705 Deleted {cases_deleted} cases")
    print(f"\u2705 Deleted {changelog_deleted} changelog entries")
    print(f"\u2705 Deleted {uploaded_deleted} uploaded file records")

    uploads_dir = os.path.join(app.root_path, 'uploads')
    if os.path.isdir(uploads_dir):
        for name in os.listdir(uploads_dir):
            path = os.path.join(uploads_dir, name)
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
        print("\u2705 Uploads folder cleared")
    else:
        print("Uploads directory not found")