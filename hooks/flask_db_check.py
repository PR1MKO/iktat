# Runs "flask db check" (model vs migration drift). If command unsupported, skip (exit 0).
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_APP", "app:create_app")

proc = subprocess.run(
    [sys.executable, "-m", "flask", "db", "check"],
    cwd=str(REPO_ROOT),
    capture_output=True,
    text=True,
)
out = (proc.stdout or "") + (proc.stderr or "")
# Some Flask-Migrate versions don’t have "db check" — treat as skip.
if "No such command 'check'" in out:
    print("Skip: 'flask db check' not supported by this Flask-Migrate version.")
    raise SystemExit(0)

print(out.strip())
raise SystemExit(proc.returncode)
