from __future__ import annotations
from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db = current_app.extensions["migrate"].db
target_metadata = db.metadata

EXAM_TABLES = {
    "investigation",
    "investigation_note",
    "investigation_attachment",
    "investigation_change_log",
}

def _is_sqlite_connection(conn) -> bool:
    try:
        return conn.dialect.name == "sqlite"
    except Exception:
        return False

def _is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")

def include_object(obj, name, type_, reflected, compare_to):
    """
    Include only the examination tables and their related objects.
    """
    if type_ == "table":
        return name in EXAM_TABLES

    # For indexes/constraints/etc., include only if their parent table is included
    parent = getattr(obj, "table", None)
    if parent is not None:
        return parent.name in EXAM_TABLES

    # Fallback (safe default)
    return False

def run_migrations_offline() -> None:
    engine = db.engines.get("examination") or db.get_engine(bind="examination")
    # Escape % for Alembic config parsing
    exam_url = engine.url.render_as_string(hide_password=False).replace("%", "%%")

    context.configure(
        url=exam_url,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table="alembic_version_examination",
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_is_sqlite_url(exam_url),  # only for SQLite
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    engine = db.engines.get("examination") or db.get_engine(bind="examination")
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            version_table="alembic_version_examination",
            compare_type=True,
            compare_server_default=True,
            render_as_batch=_is_sqlite_connection(connection),  # only for SQLite
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
