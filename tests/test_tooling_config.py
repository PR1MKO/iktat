from pathlib import Path
import re
import yaml

def test_pyproject_sections_present():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.black]" in text
    assert "[tool.isort]" in text
    assert "[tool.ruff]" in text
    assert "line-length = 88" in text
    assert 'target-version = ["py310"]' in text or 'target-version = "py310"' in text
    assert "migrations" in text and "instance" in text and "uploads" in text

def test_pre_commit_order_and_hooks():
    data = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    ids = [h["id"] for repo in data["repos"] for h in repo.get("hooks", [])]
    # Order must be Ruff -> isort -> Black
    order = [i for i in ids if i in {"ruff", "isort", "black"}]
    assert order == ["ruff", "isort", "black"]

def test_ci_runs_expected_steps():
    y = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = y["jobs"]["lint-test"]["steps"]
    cmd = "\n".join(" ".join(s.get("run","").split()) for s in steps if "run" in s)
    assert "ruff ." in cmd
    assert "black --check ." in cmd
    assert "isort --check-only ." in cmd
    assert "pytest -q" in cmd