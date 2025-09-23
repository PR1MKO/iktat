# AGENT CONTRACT — IKTATAS2.0 (Browser Codex)

## Setup rules (must follow)
- Install **only** base runtime deps from `requirements.txt`.
- **Do not** install dev/test/tooling deps (`requirements-dev.txt`) unless explicitly asked.
- **Do not** run `pytest` (or any tests) during setup or mid-task.
- If you must validate, use static checks only (imports, ruff/isort/black), no execution of tests.
- If `constraints.txt` exists, use it: `pip install -r requirements.txt -c constraints.txt`.
- Pre-commit hooks are configured to run **only on commit stage**; if you invoke `pre-commit run -a` during setup/maintenance it should do nothing.

## Workflow
1) **PLAN** → short JSON plan.
2) **EXEC** → minimal diff patches, JSON-only output (temperature≈0), no tests.
3)Run before committing: python -m pytest -q . Only commit if all tests pass successfully.

## Context rules
- Prefer `CONTEXT_PACK.md` + targeted snippets/diffs. Avoid full-file dumps.
- Keep prompts ≤ ~8k tokens. Ask for missing snippets if needed.

## Optional scripts you may call
- `codex/setup.ps1` — base deps only, **no tests**.
- `codex/maintenance.ps1` — notes/reminders, **no tests**.

> For human developer setup and tasks, see `README.md`.
