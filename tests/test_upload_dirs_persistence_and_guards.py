from __future__ import annotations

import importlib
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace


def _dummy_app(instance_path: Path, root_path: Path):
    class _App:
        def __init__(self, inst: Path, root: Path) -> None:
            self.instance_path = str(inst)
            self.root_path = str(root)

        def app_context(self):  # pragma: no cover - trivial
            return nullcontext()

    return _App(instance_path, root_path)


def test_ensure_investigation_folder_creates_keep(tmp_path, monkeypatch):
    import app.paths as paths_mod

    def fake_investigation_root() -> Path:
        return tmp_path / "instance" / "uploads_investigations"

    monkeypatch.setattr(paths_mod, "investigation_root", fake_investigation_root)

    from app.paths import ensure_investigation_folder

    cdir = ensure_investigation_folder("V-TEST-2025")
    assert (cdir / ".keep").exists()
    assert (cdir / "DO-NOT-EDIT").exists()
    assert (cdir / "DO-NOT-EDIT" / ".keep").exists()


def test_ensure_case_folder_creates_keep(tmp_path, monkeypatch):
    import app.paths as paths_mod

    def fake_case_root() -> Path:
        return tmp_path / "instance" / "uploads_cases"

    monkeypatch.setattr(paths_mod, "case_root", fake_case_root)

    from app.paths import ensure_case_folder

    cdir = ensure_case_folder("V-CASE-2025")
    assert (cdir / ".keep").exists()
    assert (cdir / "DO-NOT-EDIT").exists()
    assert (cdir / "DO-NOT-EDIT" / ".keep").exists()


def test_reset_storage_and_data_guarded(tmp_path, monkeypatch):
    module = importlib.import_module("scripts.reset_storage_and_data")
    module = importlib.reload(module)

    instance_root = tmp_path / "instance"
    cases_root = instance_root / "uploads_cases"
    inv_root = instance_root / "uploads_investigations"
    for directory in (cases_root, inv_root):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".keep").write_text("")

    dummy_app = _dummy_app(instance_root, tmp_path)

    monkeypatch.setattr(module, "create_app", lambda: dummy_app)
    monkeypatch.setattr(module, "case_root", lambda: cases_root)
    monkeypatch.setattr(module, "investigation_root", lambda: inv_root)
    monkeypatch.setattr(module, "_delete_model", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        module,
        "db",
        SimpleNamespace(session=SimpleNamespace(commit=lambda: None)),
    )

    monkeypatch.delenv("ALLOW_INSTANCE_DELETION", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)

    # 1) No confirmations -> dry-run
    module.main([])
    assert cases_root.exists()
    assert inv_root.exists()

    # 2) Only --force -> still dry-run
    module.main(["--force"])
    assert cases_root.exists()
    assert inv_root.exists()

    # 3) Only env -> still dry-run
    monkeypatch.setenv("ALLOW_INSTANCE_DELETION", "1")
    module.main([])
    assert cases_root.exists()
    assert inv_root.exists()

    # 4) Both flags + env -> allowed; directories recreated with .keep
    module.main(["--force", "--i-know-what-im-doing"])
    assert cases_root.exists()
    assert (cases_root / ".keep").exists()
    assert inv_root.exists()
    assert (inv_root / ".keep").exists()


def test_factory_reset_disabled(tmp_path):
    result = __import__("subprocess").run(
        [sys.executable, "factory_reset.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "disabled" in (result.stderr + result.stdout).lower()
