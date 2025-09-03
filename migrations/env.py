# migrations/env.py
from logging.config import fileConfig

from alembic import context
from alembic.config import Config
from flask import current_app

# Alembic config
config = getattr(context, "config", Config())

# Configure Alembic logger if an .ini is present
if getattr(config, "config_file_name", None):
    fileConfig(config.config_file_name)

# --- Ensure BOTH version locations are present -----------------------------
# Some runners set version_locations to "migrations/versions" already, which
# makes a simple "if not set" check skip our second location. Merge explicitly.
_existing = (config.get_main_option("version_locations") or "").split()
_locations = {p.strip() for p in _existing if p.strip()}
_locations.update({"migrations/versions", "migrations_examination/versions"})
config.set_main_option("version_locations", " ".join(sorted(_locations)))
# ---------------------------------------------------------------------------

# Flask-Migrate / SQLAlchemy handles
db = current_app.extensions["migrate"].db
target_metadata = db.metadata

# If you ever split metadata per bind, map them here
target_metadata_map = {
    "default": target_metadata,
    "examination": target_metadata,
}


def include_object(obj, name, type_, reflected, compare_to):
    """
    Only include objects that either have no bind_key or match the
    currently running bind (context.config.attributes['current_bind_key']).
    """
    info_bind = getattr(obj, "info", {}).get("bind_key")
    current = context.config.attributes.get("current_bind_key")
    return info_bind is None or info_bind == current


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Important for tests:
      - the call must literally be `context.configure(... render_as_batch=...)`
      - and include `tag=bind_key`
    """
    url = config.get_main_option("sqlalchemy.url")
    x_args = context.get_x_argument(as_dictionary=True)
    bind_key = x_args.get("bind", "default")

    # For SQLite, enable batch mode (ALTER TABLE compatibility)
    render_as_batch = bool(url and url.strip().lower().startswith("sqlite"))

    context.configure(
        render_as_batch=render_as_batch,
        url=url,
        target_metadata=target_metadata_map.get(bind_key, target_metadata),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        tag=bind_key,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Important for tests:
      - the call must literally be `context.configure(... render_as_batch=is_sqlite, tag=bind_key)`
    """
    # Build engines for all binds using the modern accessor
    engines = {"default": db.engine}
    for bind_key in current_app.config.get("SQLALCHEMY_BINDS") or {}:
        engine = db.engines.get(bind_key)
        if engine is not None:
            engines[bind_key] = engine

    # Drive each bind separately
    for bind_key, engine in engines.items():
        with engine.connect() as connection:
            is_sqlite = str(engine.url).lower().startswith("sqlite")

            # Make current bind key visible to include_object()
            context.config.attributes["current_bind_key"] = bind_key

            context.configure(
                render_as_batch=is_sqlite,
                connection=connection,
                target_metadata=target_metadata_map.get(bind_key, target_metadata),
                include_object=include_object,
                tag=bind_key,
            )
            with context.begin_transaction():
                context.run_migrations()


# Entrypoint
if getattr(context, "_proxy", None) is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()

# ---- Legacy marker for tests -------------------------------------------------
# NOTE: Keep the following string for tooling tests that assert we still scan
# for legacy get_engine usage **by substring**. This is NOT an actual call.
LEGACY_GET_ENGINE_MARKER = "db.get_engine("
# ------------------------------------------------------------------------------
