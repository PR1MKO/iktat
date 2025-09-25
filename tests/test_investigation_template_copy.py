import os
import shutil
import stat
import time
from pathlib import Path

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


def _rmtree_win_safe(path: Path, retries: int = 10, delay: float = 0.1) -> None:
    """
    Robust rmtree for Windows: retries and clears RO attributes on failure.
    """

    def _onerror(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
        except Exception:
            pass
        try:
            func(p)
        except Exception:
            # rethrow to be handled by retry loop
            raise

    for _ in range(retries):
        try:
            shutil.rmtree(path, onerror=_onerror)
            return
        except PermissionError:
            time.sleep(delay)
    # final attempt (raise if still locked)
    shutil.rmtree(path, onerror=_onerror)


def _reset_upload_root(app, tmp_path):
    """Point INVESTIGATIONS_UPLOAD_ROOT at a per-test temp directory."""
    root = Path(tmp_path) / "uploads_investigations"
    if root.exists():
        _rmtree_win_safe(root)
    root.mkdir(parents=True, exist_ok=True)
    app.config["INVESTIGATIONS_UPLOAD_ROOT"] = str(root)
    return root


def test_investigation_templates_copied(client, app, tmp_path):
    with app.app_context():
        create_user()
        root = _reset_upload_root(app, tmp_path)
        # Guard: never touch real instance path in tests
        # (Py<3.9 lacks Path.is_relative_to; implement manual check)
        root_str = str(root.resolve())
        tmp_str = str(Path(tmp_path).resolve())
        assert root_str.startswith(tmp_str)
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
