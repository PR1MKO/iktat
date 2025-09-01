from __future__ import annotations

import logging
import os
import sys
from logging import StreamHandler
from typing import Any, Callable

from app import create_app


def get_app():
    return create_app()


def setup_logging(level: str | None = None) -> logging.Logger:
    lvl = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    root = logging.getLogger()
    # de-dupe stdout handler
    if not any(isinstance(h, StreamHandler) for h in root.handlers):
        h = StreamHandler(sys.stdout)
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(h)
    root.setLevel(lvl)
    return root


def run_with_app(fn: Callable[..., Any], *a, **k):
    app = get_app()
    with app.app_context():
        return fn(*a, **k)
