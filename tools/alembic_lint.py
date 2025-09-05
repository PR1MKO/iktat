#!/usr/bin/env python
"""
Alembic Migration Linter (SQLite + Multi-Bind)

Dual-mode behavior:

A) Multi-bind revisions (detected if any of the following is true):
   - file defines _current_bind(), or
   - uses context.get_tag_argument(...) or context.get_x_argument(...), or
   - defines upgrade_examination()/downgrade_examination(), or
   - contains the marker:  # lint: multi-bind
   Enforce:
     - upgrade_main()/downgrade_main()/upgrade_examination()/downgrade_examination() present
     - top-level upgrade()/downgrade() call at least one per-bind function
     - ALTER-like ops inside batch_alter_table(...)
     - NOT NULL adds must have server_default (or be staged)

B) Single-bind revisions (legacy/simple) — default if none of the above, or marker:
   # lint: single-bind
   Enforce:
     - top-level upgrade()/downgrade() exist
     - ALTER-like ops inside batch_alter_table(...)
     - NOT NULL adds must have server_default (or be staged)

Notes:
- We DO NOT enforce explicit names for create_index/create_unique_constraint here,
  to avoid false positives from op.f("...") or variable names used by Alembic.
- Exit codes: 0 OK, 1 violations, 2 script error.
"""

import re
import sys
from pathlib import Path

MIG_DIR = Path("migrations") / "versions"

# ---- patterns ---------------------------------------------------------------
FUNC_UPGRADE = re.compile(r"^\s*def\s+upgrade\s*\(", re.M)
FUNC_DOWNGRADE = re.compile(r"^\s*def\s+downgrade\s*\(", re.M)

FUNC_UPGRADE_MAIN = re.compile(r"^\s*def\s+upgrade_main\s*\(", re.M)
FUNC_DOWNGRADE_MAIN = re.compile(r"^\s*def\s+downgrade_main\s*\(", re.M)
FUNC_UPGRADE_EXAM = re.compile(r"^\s*def\s+upgrade_examination\s*\(", re.M)
FUNC_DOWNGRADE_EXAM = re.compile(r"^\s*def\s+downgrade_examination\s*\(", re.M)

HAS_CURRENT_BIND = re.compile(r"^\s*def\s+_current_bind\s*\(", re.M)
USES_GET_TAG = re.compile(r"context\.get_tag_argument\s*\(")
USES_GET_XARG = re.compile(r"context\.get_x_argument\s*\(")

CALL_MAIN_IN_UPGRADE = re.compile(
    r"def\s+upgrade\s*\([^)]*\):[\s\S]*?upgrade_main\s*\(", re.M
)
CALL_EXAM_IN_UPGRADE = re.compile(
    r"def\s+upgrade\s*\([^)]*\):[\s\S]*?upgrade_examination\s*\(", re.M
)
CALL_MAIN_IN_DOWNGRADE = re.compile(
    r"def\s+downgrade\s*\([^)]*\):[\s\S]*?downgrade_main\s*\(", re.M
)
CALL_EXAM_IN_DOWNGRADE = re.compile(
    r"def\s+downgrade\s*\([^)]*\):[\s\S]*?downgrade_examination\s*\(", re.M
)

# ALTER-like ops should be inside batch_alter_table
ALTER_OPS_COMPILED = re.compile(
    "|".join(
        [
            r"add_column\s*\(",
            r"drop_column\s*\(",
            r"alter_column\s*\(",
            r"create_foreign_key\s*\(",
            r"drop_constraint\s*\(",
        ]
    )
)
BATCH_BLOCK = re.compile(r"with\s+op\.batch_alter_table\s*\(", re.M)

# NOT NULL additions without server_default
ADD_COLUMN = re.compile(r"add_column\s*\(\s*[^,]+,\s*sa\.Column\s*\(", re.S)
NULLABLE_FALSE = re.compile(r"nullable\s*=\s*False")
SERVER_DEFAULT = re.compile(r"server_default\s*=")

# Markers to force mode
FORCE_SINGLE_MARK = "lint: single-bind"
FORCE_MULTI_MARK = "lint: multi-bind"


def _is_multibind(txt: str) -> bool:
    """Heuristic to decide if a revision is multi-bind-aware."""
    if FORCE_MULTI_MARK in txt:
        return True
    if FORCE_SINGLE_MARK in txt:
        return False
    return bool(
        HAS_CURRENT_BIND.search(txt)
        or USES_GET_TAG.search(txt)
        or USES_GET_XARG.search(txt)
        or FUNC_UPGRADE_EXAM.search(txt)
        or FUNC_DOWNGRADE_EXAM.search(txt)
    )


def _check_common_rules(txt: str, errs: list[str]) -> None:
    # 3) batch_alter_table present when ALTER ops appear
    if ALTER_OPS_COMPILED.search(txt) and not BATCH_BLOCK.search(txt):
        errs.append("ALTER-like ops present without batch_alter_table() block")

    # 5) NOT NULL additions without server_default
    if ADD_COLUMN.search(txt):
        for m in ADD_COLUMN.finditer(txt):
            snippet = txt[m.start() : m.start() + 400]
            if NULLABLE_FALSE.search(snippet) and not SERVER_DEFAULT.search(snippet):
                errs.append(
                    "add_column with nullable=False but no server_default (stage it or add default)"
                )
                break


def lint_file(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    errs: list[str] = []

    if _is_multibind(txt):
        # ---- MULTI-BIND RULESET --------------------------------------------
        if not FUNC_UPGRADE_MAIN.search(txt):
            errs.append("missing upgrade_main()")
        if not FUNC_DOWNGRADE_MAIN.search(txt):
            errs.append("missing downgrade_main()")
        if not FUNC_UPGRADE_EXAM.search(txt):
            errs.append("missing upgrade_examination()")
        if not FUNC_DOWNGRADE_EXAM.search(txt):
            errs.append("missing downgrade_examination()")

        # Dispatch presence (any of the accepted mechanisms)
        if not (
            HAS_CURRENT_BIND.search(txt)
            or USES_GET_TAG.search(txt)
            or USES_GET_XARG.search(txt)
        ):
            errs.append(
                "missing bind dispatch (_current_bind() / context.get_tag_argument() / context.get_x_argument())"
            )

        # Top-level calls (at least one per-bind call in each)
        if not (CALL_MAIN_IN_UPGRADE.search(txt) or CALL_EXAM_IN_UPGRADE.search(txt)):
            errs.append(
                "upgrade() must call a per-bind function (upgrade_main() or upgrade_examination())"
            )
        if not (
            CALL_MAIN_IN_DOWNGRADE.search(txt) or CALL_EXAM_IN_DOWNGRADE.search(txt)
        ):
            errs.append(
                "downgrade() must call a per-bind function (downgrade_main() or downgrade_examination())"
            )

        _check_common_rules(txt, errs)
        return errs

    # ---- SINGLE-BIND RULESET -----------------------------------------------
    if not FUNC_UPGRADE.search(txt):
        errs.append("missing top-level upgrade()")
    if not FUNC_DOWNGRADE.search(txt):
        errs.append("missing top-level downgrade()")

    _check_common_rules(txt, errs)
    return errs


def main(argv: list[str]) -> int:
    # If specific files passed, lint only those; else lint all under migrations/versions
    if len(argv) > 1:
        files = [Path(p) for p in argv[1:] if p.endswith(".py")]
    else:
        if not MIG_DIR.exists():
            print("ERROR: migrations/versions not found", file=sys.stderr)
            return 2
        files = sorted(MIG_DIR.glob("*.py"))

    any_errors = False
    for f in files:
        errs = lint_file(f)
        if errs:
            any_errors = True
            print(f"\n✖ {f}")
            for e in errs:
                print(f"  - {e}")

    if any_errors:
        print(
            "\nFAIL: Migration lints failed.\n"
            "Fix the issues above, or (rare) force mode with a file comment:\n"
            "  # lint: single-bind   OR   # lint: multi-bind\n"
        )
        return 1

    print("OK: Migration lints passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
