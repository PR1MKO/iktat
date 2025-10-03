import logging
import shutil
from pathlib import Path

from app.models import Case
from app.paths import case_root, ensure_case_folder
from app.views.auth import init_case_upload_dirs
from tests.helpers import create_user, login


def _reset_upload_root(app):
    root = case_root()
    if root.exists():
        shutil.rmtree(root)


def test_boncolas_templates_copied(client, app):
    with app.app_context():
        create_user()
        _reset_upload_root(app)
        src_root = Path(app.instance_path) / "docs" / "boncolas"
        if src_root.exists():
            shutil.rmtree(src_root)
        src_root.mkdir(parents=True)
        (src_root / "README.txt").write_text("hello")
        forms = src_root / "forms"
        forms.mkdir()
        (forms / "blank.txt").write_text("blank")

    with client:
        login(client, "admin", "secret")
        data = {
            "case_type": "test",
            "beerk_modja": "Email",
            "temp_id": "T1",
            "institution_name": "Clinic",
        }
        resp = client.post("/cases/new", data=data, follow_redirects=False)
        assert resp.status_code == 302

    with app.app_context():
        case = Case.query.order_by(Case.id.desc()).first()
        dst_root = ensure_case_folder(case.case_number) / "DO-NOT-EDIT"
        assert (dst_root / "README.txt").exists()
        assert (dst_root / "forms" / "blank.txt").exists()
        assert not (
            ensure_case_folder(case.case_number) / "webfill-do-not-edit"
        ).exists()


def test_boncolas_missing_template_dir_warns(client, app, caplog):
    with app.app_context():
        create_user()
        _reset_upload_root(app)
        src_root = Path(app.instance_path) / "docs" / "boncolas"
        if src_root.exists():
            shutil.rmtree(src_root)

    with caplog.at_level(logging.WARNING):
        with client:
            login(client, "admin", "secret")
            data = {
                "case_type": "test",
                "beerk_modja": "Email",
                "temp_id": "T2",
                "institution_name": "Clinic",
            }
            resp = client.post("/cases/new", data=data, follow_redirects=False)
            assert resp.status_code == 302
    assert any("Case template dir missing" in r.message for r in caplog.records)


def test_init_case_dirs_idempotent(client, app):
    with app.app_context():
        create_user()
        _reset_upload_root(app)
        src_root = Path(app.instance_path) / "docs" / "boncolas"
        if src_root.exists():
            shutil.rmtree(src_root)
        src_root.mkdir(parents=True)
        (src_root / "README.txt").write_text("orig")

    with client:
        login(client, "admin", "secret")
        data = {
            "case_type": "test",
            "beerk_modja": "Email",
            "temp_id": "T3",
            "institution_name": "Clinic",
        }
        resp = client.post("/cases/new", data=data, follow_redirects=False)
        assert resp.status_code == 302

    with app.app_context():
        case = Case.query.order_by(Case.id.desc()).first()
        dst_root = ensure_case_folder(case.case_number) / "DO-NOT-EDIT"
        readme = dst_root / "README.txt"
        assert readme.read_text() == "orig"
        readme.write_text("custom")
        init_case_upload_dirs(case)
        assert readme.read_text() == "custom"
