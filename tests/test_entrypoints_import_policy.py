import re
from pathlib import Path

FILES = ["run.py", "run_tasks.py", "run_scheduler.py"]


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_factory_import_present():
    for f in FILES:
        src = read(f)
        assert re.search(
            r"^from app import create_app", src, re.M
        ), f"{f} missing create_app import"


def test_helpers_import_present():
    for f in FILES:
        src = read(f)
        assert re.search(
            r"^from app\.utils\.context import get_app, run_with_app, setup_logging",
            src,
            re.M,
        ), f"{f} missing helper imports"


def test_no_print_calls():
    for f in FILES:
        assert "print(" not in read(f), f"{f} contains print()"


def test_logging_exception_and_sys_exit():
    for f in FILES:
        src = read(f)
        assert "logging.exception(" in src, f"{f} missing logging.exception"
        assert "sys.exit(1)" in src, f"{f} missing sys.exit(1)"
