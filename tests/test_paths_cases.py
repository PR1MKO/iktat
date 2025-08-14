import os


def _n(p): return os.path.normpath(p)


def test_default_case_root(app):
    from app.paths import case_root
    with app.app_context():
        want = _n(os.path.join(app.root_path, "uploads_boncolasok"))
        assert _n(case_root()) == want


def test_ensure_case_folder_creates(app, tmp_path):
    from app.paths import ensure_case_folder
    app.config["CASE_UPLOAD_FOLDER"] = str(tmp_path / "bonc")
    with app.app_context():
        p = ensure_case_folder("CASE-0001")
        assert os.path.isdir(p)