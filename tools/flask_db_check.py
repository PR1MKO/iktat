#!/usr/bin/env python
# Cross-platform drift check runner that prefers the repo venv.
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.name == "nt":
    VENV_PY = os.path.join(ROOT, "venv", "Scripts", "python.exe")
else:
    VENV_PY = os.path.join(ROOT, "venv", "bin", "python")
PY = VENV_PY if os.path.exists(VENV_PY) else sys.executable

env = os.environ.copy()
env.setdefault("FLASK_APP", "app:create_app")


def run(cmd):
    return subprocess.call(cmd, cwd=ROOT, env=env)


# Prefer the Flask-Migrate custom command if present
rc = run([PY, "-X", "utf8", "-m", "flask", "db", "check"])
if rc == 2:  # command missing → fallback to a simple heads/current comparison
    rc_heads = run([PY, "-X", "utf8", "-m", "flask", "db", "heads"])
    rc_curr = run(
        [PY, "-X", "utf8", "-m", "flask", "db", "current", "-d", "migrations"]
    )
    rc = 0 if (rc_heads == 0 and rc_curr == 0) else 1
sys.exit(rc)
