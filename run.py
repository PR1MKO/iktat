# run.py
import logging
import sys

from app import create_app  # noqa: F401
from app.utils.context import get_app, run_with_app, setup_logging  # noqa: F401

# Expose WSGI app at module level (required by tests and WSGI servers)
app = get_app()


def _init_and_run() -> int:
    from app.tasks.smoke import ping_db

    logging.getLogger(__name__).info("smoke: %r", ping_db())
    return 0


def main() -> int:
    try:
        setup_logging()
        return run_with_app(_init_and_run)
    except Exception:
        logging.exception("run.py: fatal")
        if __name__ == "__main__":
            sys.exit(1)
        return 1


if __name__ == "__main__":
    sys.exit(main())
