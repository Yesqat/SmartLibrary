"""Migrations use an operator connection, never runtime credentials implicitly."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.db import migration_comparison, models  # noqa: F401
from app.db.base import Base

config = context.config
migration_comparison.register()
if config.config_file_name:
    fileConfig(config.config_file_name)


def run(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        compare_server_default=True,
        autogenerate_plugins=["smartlibrary.defaults", "alembic.autogenerate.*"],
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run(config.attributes["connection"])
else:
    url = os.environ.get("MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError("Set MIGRATION_DATABASE_URL or use the documented database tool")
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        run(connection)
