import os

def _n(p): return os.path.normpath(p)

def test_default_investigation_root(app):
    from app.paths import investigation_root
    with app.app_context():
        want = _n("C:\\Users\\kiss.istvan3\\Desktop\\folyamatok\\IKTATAS2.0\\forensic-case-tracker\\app\\uploads_vizsgalatok")
        assert _n(investigation_root()) == want

def test_config_override_investigation_root(app, tmp_path):
    from app.paths import investigation_root
    app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(tmp_path / "vizs")
    with app.app_context():
        got = investigation_root()
        assert _n(got) == _n(str(tmp_path / "vizs"))
        assert os.path.isdir(got)

def test_ensure_investigation_folder_creates(app, tmp_path):
    from app.paths import ensure_investigation_folder
    app.config["INVESTIGATION_UPLOAD_FOLDER"] = str(tmp_path / "vizs2")
    with app.app_context():
        p = ensure_investigation_folder("V-0001/2025")
        assert os.path.isdir(p)
