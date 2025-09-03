import importlib
import os
import sys
import traceback

# Make sure the repo root is first on sys.path
sys.path.insert(0, os.getcwd())

try:
    import app as app_pkg

    print(">>> app module path:", getattr(app_pkg, "__file__", "<no __file__>"))
except Exception:
    print("!!! failed to import local 'app' package")
    traceback.print_exc()
    raise

try:
    from app import create_app, db
except Exception:
    print("!!! failed to import create_app or db from app")
    traceback.print_exc()
    raise

# Try to import the investigations models explicitly and show file
try:
    inv = importlib.import_module("app.investigations.models")
    print(">>> investigations models path:", getattr(inv, "__file__", "<no __file__>"))
except Exception:
    print("!!! failed to import app.investigations.models")
    traceback.print_exc()

app = create_app()
with app.app_context():
    # Force-load the aggregator (should import investigations + core)
    try:
        import app.models_all  # noqa: F401

        print(">>> imported app.models_all OK")
    except Exception:
        print("!!! failed to import app.models_all")
        traceback.print_exc()

    tables = sorted(k for k in db.metadata.tables.keys())
    print(">>> tables in metadata:", tables)
    print(">>> investigation in metadata?", "investigation" in db.metadata.tables)
