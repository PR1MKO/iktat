# AGENT CONTRACT — IKTATAS2.0 (Browser Codex)

## Setup rules
- Install only base runtime deps from `requirements.txt` (use `-c constraints.txt` if present).
- Do NOT install dev/test/tooling deps during setup.
- Do NOT run tests during setup.

## Workflow (HARD GATES)
1) PLAN → output a short JSON plan.
2) EXEC → propose minimal, surgical diffs as JSON (no file dumps).
3) VALIDATE (MANDATORY) → run:
   - python --version
   - pip --version
   - python -m pytest -q
   If tests fail or did not run: STOP and return:
   {
     "status": "blocked",
     "reason": "pytest_failed_or_not_run",
     "pytest_tail": "<last 80 lines>"
   }
4) COMMIT → Only if step 3 passed:
   - Commit ONLY touched files for this task.

## Test dependency rule
- If tests error due to missing dev deps (e.g., bs4, pytest plugins), install exactly what’s needed via `requirements-dev.txt` and re-run `python -m pytest -q`. This exception is allowed ONLY inside step 3 (VALIDATE).

## Context rules
- Prefer CONTEXT_PACK.md + targeted snippets/diffs; keep prompts ≤ 8k tokens.

## Pre-commit
- Pre-commit hooks run only at commit; do not invoke them manually.

## Always
- Run `python -m pytest` before committing; if any test fails, repair it and only commit when all tests pass successfully.
