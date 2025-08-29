from __future__ import annotations

import os

from tools.devdoc import append_entry


def test_double_append_and_order(tmp_path):
    target = tmp_path / "DEV.md"
    append_entry("H1", "R1", "N1", path=str(target))
    append_entry("H2", "R2", "N2", path=str(target))
    content = target.read_text(encoding="utf-8")
    assert content.count("**Heads:**") == 2
    assert content.count("**Risks:**") == 2
    assert content.count("**Next:**") == 2
    assert content.count("---") == 2
    headers = [line for line in content.splitlines() if line.startswith("### ")]
    assert len(headers) == 2
    for header in headers:
        assert " / " in header
    assert content.index("H1") < content.index("H2")
    assert content.endswith("\n")


def test_env_override(tmp_path, monkeypatch):
    env_path = tmp_path / "ENV_DEV.md"
    monkeypatch.setenv("DEV_DOC_PATH", str(env_path))
    append_entry("E1", "R1", "N1")
    assert env_path.exists()
    content = env_path.read_text(encoding="utf-8")
    assert "**Heads:**" in content
    assert content.endswith("\n")
	