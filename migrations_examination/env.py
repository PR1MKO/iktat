# migrations_examination/env.py
from __future__ import with_statement
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from flask import current_app

from app import create_app, db

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# All your exam models share the same metadata object
target_metadata = db.metadata

def run_migrations_offline() -> None:
    app = create_app()
    with app.app_context():
        url = app.config['SQLALCHEMY_BINDS']['examination']
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            version_table='alembic_version_examination',
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()

def run_migrations_online() -> None:
    app = create_app()
    with app.app_context():
        connectable = db.get_engine(app, bind='examination')  # <-- force the exam bind
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table='alembic_version_examination',  # <-- separate version table
                compare_type=True,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
