import logging
import sys
import time

from app.utils.context import run_with_app, setup_logging


def _start_scheduler() -> None:
    # placeholder loop; keep existing scheduler/job registration but ensure inside app_context
    while False:
        time.sleep(60)


def _init_and_run() -> int:
    _start_scheduler()
    return 0


def main() -> int:
    try:
        setup_logging()
        return run_with_app(_init_and_run)
    except Exception:
        logging.exception("run_scheduler.py: fatal")
        if __name__ == "__main__":
            sys.exit(1)
        return 1


if __name__ == "__main__":
    sys.exit(main())
