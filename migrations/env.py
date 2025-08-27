from logging.config import fileConfig

from alembic import context
from alembic.config import Config
from flask import current_app


config = getattr(context, "config", Config())

# ensure the Alembic logger config is set up
if getattr(config, "config_file_name", None):
    fileConfig(config.config_file_name)
    
# Support multiple version locations (default + examination)
version_locations = config.get_main_option("version_locations")
if not version_locations:
    config.set_main_option(
        "version_locations",
        "migrations/versions migrations_examination/versions",
    )


db = current_app.extensions["migrate"].db
target_metadata = db.metadata
# Optional map if metadata ever splits per bind
target_metadata_map = {
    "default": target_metadata,
    "examination": target_metadata,
}


def include_object(object, name, type_, reflected, compare_to):
    info_bind = getattr(object, "info", {}).get("bind_key")
    current = context.config.attributes.get("current_bind_key")
    return info_bind is None or info_bind == current


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    bind_key = context.get_x_argument(as_dictionary=True).get("bind", "default")
    render_as_batch = bool(url and url.startswith("sqlite"))

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
    engines = {"default": db.engine}
    binds = dict(current_app.config.get("SQLALCHEMY_BINDS") or {})
    for bind_key in binds:
        engines[bind_key] = db.get_engine(current_app, bind=bind_key)

    for bind_key, engine in engines.items():
        with engine.connect() as connection:
            is_sqlite = str(engine.url).startswith("sqlite")
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


if getattr(context, "_proxy", None) is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
