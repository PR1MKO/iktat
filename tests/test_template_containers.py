import json
import subprocess
import sys
from pathlib import Path


def test_jinja_containers_are_balanced() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "audit_containers.py"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        result.returncode == 0
    ), f"audit_containers.py failed:\n{result.stdout}\n{result.stderr}"
    report = json.loads(result.stdout)
    assert not report.get(
        "issues"
    ), f"Template container issues detected: {report['issues']}"
