from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db = current_app.extensions["migrate"].db
target_metadata = db.metadata

# Tables that belong to the "examination" bind
EXAM_TABLES = {
    "investigation",
    "investigation_note",
    "investigation_attachment",
    "investigation_change_log",
}
EXAM_INDEX_PREFIXES = ("ix_investigation_", "ux_investigation_")


def _is_sqlite_connection(conn) -> bool:
    try:
        return conn.dialect.name == "sqlite"
    except Exception:
        return False


def _is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")


def include_object(obj, name, type_, reflected, compare_to):
    """Include only the examination tables (and related objects)."""
    if type_ == "table":
        return name in EXAM_TABLES

    parent = getattr(obj, "table", None)
    if parent is not None and type_ in {
        "index",
        "unique_constraint",
        "foreign_key_constraint",
    }:
        return parent.name in EXAM_TABLES or name.startswith(EXAM_INDEX_PREFIXES)

    return False


def _get_exam_engine():
    engine = db.engines.get("examination")
    if engine is None:
        raise RuntimeError(
            "No engine registered for bind 'examination'. "
            "Ensure SQLALCHEMY_BINDS['examination'] is configured and the app initialized."
        )
    return engine


def run_migrations_offline() -> None:
    engine = _get_exam_engine()
    exam_url = engine.url.render_as_string(hide_password=False).replace("%", "%%")

    context.config.attributes["current_bind_key"] = "examination"

    context.configure(
        url=exam_url,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table="alembic_version_examination",
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_is_sqlite_url(exam_url),
        literal_binds=True,
        tag="examination",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = _get_exam_engine()
    with engine.connect() as connection:
        context.config.attributes["current_bind_key"] = "examination"

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            version_table="alembic_version_examination",
            compare_type=True,
            compare_server_default=True,
            render_as_batch=_is_sqlite_connection(connection),
            tag="examination",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
