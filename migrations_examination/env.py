from __future__ import with_statement
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


def include_object(object, name, type_, reflected, compare_to):
    # exam repo: include only the investigation* tables
    if type_ == "table":
        return name in EXAM_TABLES
    # allow indexes/constraints that belong to included tables
    return True

def run_migrations_offline() -> None:
    exam_url = str(db.get_engine(current_app, bind="examination").url)
    context.configure(
        url=exam_url,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table="alembic_version_examination",
        compare_type=True,
        render_as_batch=True,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = db.get_engine(current_app, bind="examination")
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            version_table="alembic_version_examination",
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
