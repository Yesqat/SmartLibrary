"""Real dependency I/O. Do not expose connection details in readiness responses."""

from typing import Literal

from redis import Redis
from sqlalchemy import Engine, text

from app.schemas.health import Readiness


def check_postgres(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            return bool(connection.scalar(text("SELECT 1")) == 1)
    except Exception:
        return False


def check_redis(client: Redis) -> bool:
    try:
        return bool(client.ping())
    except Exception:
        return False


def readiness(engine: Engine, client: Redis) -> Readiness:
    dependencies: dict[str, Literal["ok", "unavailable"]] = {
        "postgres": "ok" if check_postgres(engine) else "unavailable",
        "redis": "ok" if check_redis(client) else "unavailable",
    }
    return Readiness(
        status="ready" if all(v == "ok" for v in dependencies.values()) else "unavailable",
        dependencies=dependencies,
    )
