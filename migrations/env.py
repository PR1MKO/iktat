import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
db_ext = current_app.extensions.get('migrate')
db = getattr(db_ext, 'db', None)
target_metadata = getattr(db, 'metadata', None)

def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects for multi-bind runs: only migrate tables that match the current bind.
    Uses Table.info['bind_key'] or model __bind_key__ to decide.
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
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    render_as_batch = _is_sqlite_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        render_as_batch=render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    default_engine = get_engine()
    binds = dict(current_app.config.get("SQLALCHEMY_BINDS") or {})

    def _configure_and_run(connection: Connection, bind_key: str | None):
        context.config.attributes["current_bind_key"] = bind_key
        render_as_batch = (connection.dialect.name == "sqlite")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=render_as_batch,
            **conf_args
        )
        with context.begin_transaction():
            context.run_migrations()

    with default_engine.connect() as connection:
        _configure_and_run(connection, bind_key=None)

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
