import logging
import sys

from app.utils.context import get_app, run_with_app, setup_logging  # noqa: F401


def _init_and_run() -> int:
    from app.tasks.smoke import ping_db

    logging.getLogger(__name__).info("smoke: %r", ping_db())
    return 0


def main() -> int:
    try:
        setup_logging()
        return run_with_app(_init_and_run)
    except Exception:
        logging.exception("run_tasks.py: fatal")
        if __name__ == "__main__":
            sys.exit(1)
        return 1


if __name__ == "__main__":
    sys.exit(main())
