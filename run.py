# run.py
import logging
import sys

from app.utils.context import get_app, setup_logging

app = get_app()


def main() -> int:
    setup_logging()
    try:
        host = "0.0.0.0"
        port = 5000
        debug = False
        app.run(host=host, port=port, debug=debug)
        return 0
    except Exception:
        logging.exception("run.py: fatal")
        return 1


if __name__ == "__main__":
    sys.exit(main())
