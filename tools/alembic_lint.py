#!/usr/bin/env python
"""
Alembic Migration Linter (SQLite + Multi-Bind)

Checks each migration file for:
  1) Per-bind functions: upgrade_main(), upgrade_examination(), and matching downgrades.
  2) upgrade()/downgrade() call both per-bind functions.
  3) SQLite-safe batch mode for ALTERs (batch_alter_table).
  4) Named constraints/indexes (create_unique_constraint/create_index with explicit names).
  5) NOT NULL column additions must have a server_default or be added nullable first.

Exit codes:
  0 = OK, 1 = Violations found, 2 = Script error
"""

import re
import sys
from pathlib import Path

MIG_DIR = Path("migrations") / "versions"

# Simple patterns (text-based; robust enough for our style)
FUNC_UPGRADE_MAIN = re.compile(r"^\s*def\s+upgrade_main\s*\(", re.M)
FUNC_DOWNGRADE_MAIN = re.compile(r"^\s*def\s+downgrade_main\s*\(", re.M)
FUNC_UPGRADE_EXAM = re.compile(r"^\s*def\s+upgrade_examination\s*\(", re.M)
FUNC_DOWNGRADE_EXAM = re.compile(r"^\s*def\s+downgrade_examination\s*\(", re.M)

CALL_UPGRADE_MAIN = re.compile(
    r"^\s*def\s+upgrade\s*\(.*?\):.*?upgrade_main\s*\(", re.S | re.M
)
CALL_UPGRADE_EXAM = re.compile(
    r"^\s*def\s+upgrade\s*\(.*?\):.*?upgrade_examination\s*\(", re.S | re.M
)
CALL_DOWNGRADE_MAIN = re.compile(
    r"^\s*def\s+downgrade\s*\(.*?\):.*?downgrade_main\s*\(", re.S | re.M
)
CALL_DOWNGRADE_EXAM = re.compile(
    r"^\s*def\s+downgrade\s*\(.*?\):.*?downgrade_examination\s*\(", re.S | re.M
)

# ALTER-ish ops that should be inside batch_alter_table
ALTER_OPS = [
    r"add_column\s*\(",
    r"drop_column\s*\(",
    r"alter_column\s*\(",
    r"create_foreign_key\s*\(",
    r"drop_constraint\s*\(",
]
ALTER_OPS_COMPILED = re.compile("|".join(ALTER_OPS))

BATCH_BLOCK = re.compile(r"with\s+op\.batch_alter_table\s*\(", re.M)

# Named constraints / indexes
NEEDS_NAME = [
    (re.compile(r"op\.create_unique_constraint\s*\("), "create_unique_constraint"),
    (re.compile(r"op\.create_index\s*\("), "create_index"),
]
HAS_STRING_ARG = re.compile(
    r"op\.(create_unique_constraint|create_index)\s*\(\s*['\"][^'\"]+['\"]"
)

# NOT NULL without default: look for Column(..., nullable=False) added
ADD_COLUMN = re.compile(r"add_column\s*\(\s*[^,]+,\s*sa\.Column\s*\(", re.S)
NULLABLE_FALSE = re.compile(r"nullable\s*=\s*False")
SERVER_DEFAULT = re.compile(r"server_default\s*=")


def lint_file(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []

    # 1) per-bind functions
    if not FUNC_UPGRADE_MAIN.search(txt):
        errors.append("missing upgrade_main()")
    if not FUNC_DOWNGRADE_MAIN.search(txt):
        errors.append("missing downgrade_main()")
    if not FUNC_UPGRADE_EXAM.search(txt):
        errors.append("missing upgrade_examination()")
    if not FUNC_DOWNGRADE_EXAM.search(txt):
        errors.append("missing downgrade_examination()")

    # 2) top-level upgrade/downgrade call both
    if not CALL_UPGRADE_MAIN.search(txt):
        errors.append("upgrade() does not call upgrade_main()")
    if not CALL_UPGRADE_EXAM.search(txt):
        errors.append("upgrade() does not call upgrade_examination()")
    if not CALL_DOWNGRADE_MAIN.search(txt):
        errors.append("downgrade() does not call downgrade_main()")
    if not CALL_DOWNGRADE_EXAM.search(txt):
        errors.append("downgrade() does not call downgrade_examination()")

    # 3) batch_alter_table present when ALTER ops appear
    if ALTER_OPS_COMPILED.search(txt) and not BATCH_BLOCK.search(txt):
        errors.append("ALTER-like ops present without batch_alter_table() block")

    # 4) named constraints/indexes
    for pat, label in NEEDS_NAME:
        if pat.search(txt) and not HAS_STRING_ARG.search(txt):
            errors.append(
                f"{label} appears without an explicit name (first arg must be a string)"
            )

    # 5) NOT NULL additions without server_default
    if ADD_COLUMN.search(txt):
        for m in ADD_COLUMN.finditer(txt):
            snippet = txt[m.start() : m.start() + 300]
            if NULLABLE_FALSE.search(snippet) and not SERVER_DEFAULT.search(snippet):
                errors.append(
                    "add_column with nullable=False but no server_default "
                    "(consider two-step migration or default)"
                )
                break

    return errors


def main(argv: list[str]) -> int:
    # If specific files passed, lint only those; else lint all under migrations/versions
    files: list[Path] = []
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
            "Fix the issues above, or mark intentional exceptions with a comment and re-run."
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
