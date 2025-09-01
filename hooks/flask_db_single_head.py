# Robust single-head check using Alembic only (no Flask-Migrate dependency)
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

# Adjust if your migrations dir isn't named "migrations"
MIGRATIONS_DIR = REPO_ROOT / "migrations"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


def load_alembic_config() -> Config:
    if ALEMBIC_INI.exists():
        cfg = Config(str(ALEMBIC_INI))
        # Ensure script_location is correct even if ini is minimal
        cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        return cfg
    # Fallback: construct config in code
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print(f"ERROR: migrations directory not found at: {MIGRATIONS_DIR}")
        return 2

    cfg = load_alembic_config()
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()  # list of revision ids

    if not heads:
        print("No Alembic heads detected — unexpected. Check your migrations tree.")
        return 2
    if len(heads) > 1:
        print("Multiple Alembic heads detected:")
        for h in heads:
            print("  ", h)
        return 1
    print("Single Alembic head OK:", heads[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
