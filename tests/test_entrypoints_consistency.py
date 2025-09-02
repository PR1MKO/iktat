import ast
import re
from pathlib import Path

FILES = ["run.py", "run_tasks.py", "run_scheduler.py"]


def read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8")


def imports_get_app_from_context(src: str) -> bool:
    t = ast.parse(src)
    for node in ast.walk(t):
        if isinstance(node, ast.ImportFrom) and node.module == "app.utils.context":
            if any(getattr(n, "name", "") == "get_app" for n in node.names):
                return True
    return False


def test_same_factory_import():
    for f in FILES:
        assert imports_get_app_from_context(
            read(f)
        ), f"{f} must import get_app from app.utils.context"


def test_run_exposes_wsgi_app():
    src = read("run.py")
    assert re.search(
        r"^app\s*=\s*get_app\(\)", src, re.M
    ), "run.py must define module-level app"


def test_main_guards_exist():
    for f in FILES:
        assert '__name__ == "__main__"' in read(f), f"{f} missing __main__ guard"


def test_tasks_and_scheduler_use_app_context():
    for f in ["run_tasks.py", "run_scheduler.py"]:
        assert "run_with_app(" in read(f), f"{f} must wrap work via run_with_app()"
