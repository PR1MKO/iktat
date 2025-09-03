import importlib
import os
import sys
import traceback

sys.path.insert(0, os.getcwd())

from app import create_app, db


def dump_registry():
    print("\n=== Registry mappers (class -> table) ===")
    try:
        mappers = list(db.Model.registry.mappers)
    except Exception as e:
        print("Failed to read registry.mappers:", e)
        mappers = []
    for m in mappers:
        try:
            cls = m.class_
            tbl = getattr(cls, "__table__", None)
            print(
                f"  {cls.__module__}.{cls.__name__} -> {getattr(tbl,'fullname',getattr(tbl,'name',None))}"
            )
        except Exception as e:
            print("  (error showing mapper):", e)


def show_investigation(module):
    print("\n=== Investigation class introspection ===")
    inv = getattr(module, "Investigation", None)
    if inv is None:
        print("Investigation class NOT found in app.investigations.models")
        return
    print("Investigation class found:", inv)
    print("  bases:", [b.__name__ for b in inv.__mro__[:5]])
    tbl = getattr(inv, "__table__", None)
    print("  __table__ exists? ", tbl is not None)
    if tbl is not None:
        print("  __table__.name:", tbl.name)
        print("  __table__.metadata is db.metadata? ", tbl.metadata is db.metadata)
        print("  __table__.info:", dict(tbl.info or {}))


def main():
    app = create_app()
    with app.app_context():
        # Import explicitly and via aggregator to ensure execution
        inv_mod = importlib.import_module("app.investigations.models")
        try:
            import app.models_all  # noqa: F401
        except Exception:
            traceback.print_exc()

        # What tables are in THIS metadata right now?
        print(">>> metadata tables:", sorted(db.metadata.tables.keys()))
        print(
            ">>> has 'investigation' in metadata? ",
            "investigation" in db.metadata.tables,
        )

        # Introspect the class + registry
        show_investigation(inv_mod)
        dump_registry()


if __name__ == "__main__":
    main()
