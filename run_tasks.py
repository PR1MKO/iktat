import logging
import sys

from app.utils.context import get_app, setup_logging


def _run_once() -> int:
    app = get_app()
    setup_logging()
    with app.app_context():
        from app.tasks.smoke import ping_db

        logging.getLogger(__name__).info("smoke: %r", ping_db())
        return 0


def main() -> int:
    try:
        return _run_once()
    except Exception:
        logging.exception("run_tasks.py: fatal")
        return 1


if __name__ == "__main__":
    sys.exit(main())
