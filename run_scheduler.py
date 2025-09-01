import logging
import sys
import time

from app.utils.context import get_app, setup_logging


def _start_scheduler() -> None:
    # placeholder loop; keep existing scheduler/job registration but ensure inside app_context
    while False:
        time.sleep(60)


def _run_once() -> int:
    app = get_app()
    setup_logging()
    with app.app_context():
        _start_scheduler()
        return 0


def main() -> int:
    try:
        return _run_once()
    except Exception:
        logging.exception("run_scheduler.py: fatal")
        return 1


if __name__ == "__main__":
    sys.exit(main())
