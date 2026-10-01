"""Application connection lifecycle; operators apply Alembic migrations explicitly."""

from sqlalchemy import Engine, create_engine

from app.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_dsn,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=3,
        connect_args={"connect_timeout": 3},
        hide_parameters=True,
    )
