import shutil

from app.investigations.models import Investigation
from app.investigations.utils import init_investigation_upload_dirs
from app.paths import ensure_investigation_folder, investigation_root
from tests.helpers import create_user, login


def _base_form_data():
    return {
        "subject_name": "Teszt Alany",
        "mother_name": "Teszt Anya",
        "birth_place": "Budapest",
        "birth_date": "2000-01-02",
        "taj_number": "123456789",
        "residence": "Cím",
        "citizenship": "magyar",
        "institution_name": "Intézet",
        "investigation_type": "type1",
        "other_identifier": "OID",
        "assignment_type": "INTEZETI",
    }


def _reset_upload_root(app):
    root = investigation_root()
    if root.exists():
        shutil.rmtree(root)


def test_investigation_templates_copied(client, app, tmp_path):
    with app.app_context():
        create_user()
        _reset_upload_root(app)
        src_root = tmp_path / "vizsgalat"
        if src_root.exists():
            shutil.rmtree(src_root)
        src_root.mkdir(parents=True)
        (src_root / "README.txt").write_text("hello")
        forms = src_root / "forms"
        forms.mkdir()
        (forms / "blank.txt").write_text("blank")
        app.config["INVESTIGATION_TEMPLATE_DIR"] = str(src_root)

    with client:
        login(client, "admin", "secret")
        resp = client.post(
            "/investigations/new", data=_base_form_data(), follow_redirects=False
        )
        assert resp.status_code == 302

    with app.app_context():
        inv = Investigation.query.order_by(Investigation.id.desc()).first()
        case_dir = ensure_investigation_folder(inv.case_number)
        dst_root = case_dir / "DO-NOT-EDIT"
        assert (dst_root / "README.txt").exists()
        assert (dst_root / "forms" / "blank.txt").exists()
        assert not (case_dir / "webfill-do-not-edit").exists()

        readme = dst_root / "README.txt"
        readme.write_text("custom")
        init_investigation_upload_dirs(inv.case_number)
        assert readme.read_text() == "custom"
