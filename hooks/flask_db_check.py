# Runs "flask db check" (model vs migration drift). If command unsupported, skip (exit 0).
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

# Ensure FLASK_APP is defined for this process
os.environ.setdefault("FLASK_APP", "app:create_app")

# 🔒 Ensure models are registered in metadata for this Python process too
try:
    from app import create_app

    app = create_app()
    with app.app_context():
        import app.models_all  # noqa: F401
except Exception as _e:
    # Don't hard-fail on import issues here; let `flask db check` report accurately.
    print(f"[flask-db-check] Warning: prelude import issue: {_e}")

# Run the check
proc = subprocess.run(
    [sys.executable, "-m", "flask", "db", "check"],
    cwd=str(REPO_ROOT),
    capture_output=True,
    text=True,
)

out = (proc.stdout or "") + (proc.stderr or "")
# Some Flask-Migrate versions don’t have "db check" — treat as skip.
if "No such command 'check'" in out or "Error: No such command 'check'." in out:
    print("Skip: 'flask db check' not supported by this Flask-Migrate version.")
    raise SystemExit(0)

print(out.strip())
raise SystemExit(proc.returncode)
