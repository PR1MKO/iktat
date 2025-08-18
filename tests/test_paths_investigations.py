from pathlib import Path

def test_default_investigation_root(app):
    from app.paths import investigation_root
    with app.app_context():
        want = Path(app.instance_path) / "uploads_investigations"
        assert investigation_root() == want


def test_config_override_investigation_root(app, tmp_path):
    from app.paths import investigation_root
    app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(tmp_path / "vizs")
    with app.app_context():
        got = investigation_root()
        assert got == Path(tmp_path / "vizs")
        assert got.is_dir()

def test_ensure_investigation_folder_creates(app, tmp_path):
    from app.paths import ensure_investigation_folder
    app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(tmp_path / "vizs2")
    with app.app_context():
        p = ensure_investigation_folder("V-0001/2025")
        assert p.is_dir()
        
