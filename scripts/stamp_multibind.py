"""Stamp all configured binds to their current head if alembic_version is missing.
Usage: python scripts/stamp_multibind.py [default|examination|all]
"""

import sys

from flask import Flask
from alembic import command
from alembic.config import Config

from app import create_app


def main() -> None:
    app: Flask = create_app()
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    cfg = Config("alembic.ini")

    with app.app_context():
        targets = ["default", "examination"] if which == "all" else [which]
        for bind in targets:
            command.stamp(cfg, "head", sql=False, tag=bind)


if __name__ == "__main__":
    main()
