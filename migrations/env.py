import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
from sqlalchemy import engine_from_config, pool
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


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects for multi-bind runs: only migrate tables that match the
    current bind. Uses Table.info['bind_key'] or model __bind_key__.
    """
    cur_bind = context.config.attributes.get("current_bind_key")
    if cur_bind:
        info_bind = None
        try:
            info_bind = getattr(object, "info", {}).get("bind_key")
        except Exception:
            info_bind = None
        if info_bind is not None:
            return info_bind == cur_bind
    return True


def _is_sqlite_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    render_as_batch = _is_sqlite_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        render_as_batch=render_as_batch,  # specified exactly once
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode'."""

    # Avoid autogenerate files when no changes
    def process_revision_directives(context_, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    # Copy and sanitize Flask-Migrate's configure_args to avoid duplicates
    raw_conf_args = current_app.extensions["migrate"].configure_args or {}
    conf_args = dict(raw_conf_args)  # shallow copy

    # Provide PRD if missing
    conf_args.setdefault("process_revision_directives", process_revision_directives)

    # Strip any keys we set explicitly to prevent:
    # TypeError: context.configure() got multiple values for keyword argument '...'
    for k in (
        "connection",
        "url",
        "target_metadata",
        "include_object",
        "render_as_batch",
        "compare_type",
        "compare_server_default",
        # extras that sometimes appear; safe to pop
        "version_table",
        "literal_binds",
        "include_schemas",
        "dialect_opts",
        "transaction_per_migration",
    ):
        conf_args.pop(k, None)

    default_engine = get_engine()
    binds = dict(current_app.config.get("SQLALCHEMY_BINDS") or {})

    def _configure_and_run(connection: Connection, bind_key: str | None):
        context.config.attributes["current_bind_key"] = bind_key
        is_sqlite = connection.dialect.name == "sqlite"

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,  # specified exactly once
            **conf_args,  # sanitized above
        )
        with context.begin_transaction():
            context.run_migrations()

    # Default / primary bind
    with default_engine.connect() as connection:
        _configure_and_run(connection, bind_key=None)

    # Secondary binds (if any)
    for bind_key, url in binds.items():
        section = f"{config.config_ini_section}.{bind_key}"
        config.set_section_option(section, "sqlalchemy.url", url)
        engine = engine_from_config(
            config.get_section(config.config_ini_section),
            url=url,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with engine.connect() as connection:
            _configure_and_run(connection, bind_key=bind_key)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
