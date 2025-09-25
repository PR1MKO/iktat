import os
from pathlib import Path

from app.paths import case_root, investigation_root


def test_upload_roots_are_tmp_not_instance(app):
    with app.app_context():
        cases = Path(case_root())
        inv = Path(investigation_root())

        assert os.sep + "instance" + os.sep not in str(cases), str(cases)
        assert os.sep + "instance" + os.sep not in str(inv), str(inv)

        assert cases.is_dir()
        assert inv.is_dir()

        (cases / ".keep").touch(exist_ok=True)
        (inv / ".keep").touch(exist_ok=True)
