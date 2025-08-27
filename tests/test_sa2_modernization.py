"""Static checks for SQLAlchemy 2.x-safe engine access patterns."""

from __future__ import annotations

import pathlib
import re


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_no_legacy_get_engine_with_app():
    """Ensure db.get_engine is never called with a Flask app."""
    pattern = re.compile(r"db\.get_engine\s*\(\s*current_app")
    for path in REPO_ROOT.rglob("*.py"):
        if "venv" in path.parts or path.name == "test_sa2_modernization.py":
            continue
        assert not pattern.search(read(path)), f"legacy get_engine in {path}"


def test_env_files_use_db_engines():
    env_paths = [
        REPO_ROOT / "migrations" / "env.py",
        REPO_ROOT / "migrations_examination" / "env.py",
    ]
    for path in env_paths:
        content = read(path)
        assert "db.engines" in content
        legacy = "db.get_engine" + "(current_app"
        assert legacy not in content


def test_script_uses_db_engines_accessor():
    path = REPO_ROOT / "scripts" / "reset_storage_and_data_2.py"
    content = read(path)
    assert "db.engines" in content
    assert "db.get_engine(" in content
    legacy = "db.get_engine" + "(current_app"
    assert legacy not in content
	