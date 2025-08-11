import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context
from sqlalchemy import MetaData

from app import db


def get_engine():
    return db.get_engine(current_app, bind='examination')


def get_engine_url():
    return str(get_engine().url).replace('%', '%%')


config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')
config.set_main_option('sqlalchemy.url', get_engine_url())


def get_metadata():
    metadata = MetaData()
    for table in db.metadata.tables.values():
        if table.info.get('bind_key') == 'examination':
            table.tometadata(metadata)
    return metadata


def run_migrations_offline():
    url = current_app.config['SQLALCHEMY_BINDS']['examination']
    context.configure(url=url, target_metadata=get_metadata(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=get_metadata())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()