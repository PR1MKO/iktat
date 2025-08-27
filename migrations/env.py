import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
from sqlalchemy.engine import Connection

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_engine():
    try:
        # Flask-SQLAlchemy < 3 / Alchemical
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        # Flask-SQLAlchemy >= 3
        return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# Model metadata for autogenerate
config.set_main_option("sqlalchemy.url", get_engine_url())
db_ext = current_app.extensions.get("migrate")
db = getattr(db_ext, "db", None)
target_metadata = getattr(db, "metadata", None)


def include_object(obj, name, type_, reflected, compare_to):
    """
    Default tree: include everything (this tree is for the primary DB only).
    """
    # If you later tag tables with obj.info["bind_key"], you can filter here.
    return True


def _is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")


def run_migrations_offline():
    """Run migrations in 'offline' mode'."""
    url = config.get_main_option("sqlalchemy.url")
    render_as_batch = _is_sqlite_url(url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=render_as_batch,     # exactly once
        version_table="alembic_version",     # explicit
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode'."""

    def process_revision_directives(context_, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    # Copy and sanitize Flask-Migrate's configure_args to avoid duplicates
    raw_conf_args = current_app.extensions["migrate"].configure_args or {}
    conf_args = dict(raw_conf_args)
    conf_args.setdefault("process_revision_directives", process_revision_directives)
    for k in (
        "connection",
        "url",
        "target_metadata",
        "include_object",
        "render_as_batch",
        "compare_type",
        "compare_server_default",
        "version_table",
        "literal_binds",
        "include_schemas",
        "dialect_opts",
        "transaction_per_migration",
    ):
        conf_args.pop(k, None)

    default_engine = get_engine()

    def _configure_and_run(connection: Connection):
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,       # exactly once
            version_table="alembic_version", # explicit
            **conf_args,
        )
        with context.begin_transaction():
            context.run_migrations()

    # IMPORTANT: default tree handles ONLY the primary DB (no binds here)
    with default_engine.connect() as connection:
        _configure_and_run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
