from pathlib import Path


def test_default_case_root(app):
    from app.paths import case_root

    with app.app_context():
        want = Path(app.instance_path) / "uploads_cases"
        assert case_root() == want


def test_ensure_case_folder_creates(app, tmp_path):
    from app.paths import ensure_case_folder

    app.config["CASE_UPLOAD_FOLDER"] = str(tmp_path / "bonc")
    with app.app_context():
        p = ensure_case_folder("CASE-0001")
        assert p.is_dir()
