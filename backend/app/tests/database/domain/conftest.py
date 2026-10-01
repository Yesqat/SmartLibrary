"""Committed domain operations use their own disposable PostgreSQL database."""

from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import update

from app.ai.embeddings.encoder import PROFILES
from app.core.config import Settings
from app.db.enums import UserRole
from app.db.manage import engine, upgrade, url
from app.db.models import User
from app.main import create_app
from app.tests.database.test_auth import login, register


@pytest.fixture(scope="session")
def domain_database(test_database_name):
    name = "smartlibrary_test_" + uuid4().hex
    owner = engine("admin", "postgres")
    created = False
    try:
        with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            created = True
        upgrade(name)
        yield name
    finally:
        if created:
            with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.connection.driver_connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                )
        owner.dispose()


@pytest.fixture(scope="session")
def domain_db(domain_database):
    db = engine("migration", domain_database)
    yield db
    db.dispose()


@pytest.fixture
def client(domain_database, settings, tmp_path):
    values = settings.model_dump()
    configured = Settings()
    values.update(
        database_url=url("runtime", domain_database).render_as_string(hide_password=False),
        redis_url=configured.redis_dsn,
        auth_rate_namespace="smartlibrary:test:domain:" + uuid4().hex,
        upload_directory=tmp_path,
        qr_encryption_key=Fernet.generate_key().decode(),
        auth_login_ip_limit=1000,
        auth_register_limit=1000,
    )
    app = create_app(Settings(**values))
    with TestClient(app) as client:
        client.headers["Origin"] = "http://localhost:8080"
        yield client
        keys = list(app.state.redis.scan_iter(match=app.state.settings.auth_rate_namespace + ":*"))
        if keys:
            app.state.redis.delete(*keys)


@pytest.fixture
def actor(client, domain_db):
    def create(role=UserRole.LIBRARIAN):
        email, user = register(client)
        with domain_db.begin() as db:
            db.execute(update(User).where(User.id == user["id"]).values(role=role))
        response = login(client, email)
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        return user, token

    return create


@pytest.fixture
def staff(client, actor):
    actor()
    return client


@pytest.fixture
def model_settings(client):
    configured = Settings()
    cache = configured.model_cache_directory
    assert Path(cache).is_dir(), "Mount the downloaded pinned models with MODEL_CACHE_DIRECTORY"
    return client.app.state.settings.model_copy(
        update={
            "embedding_model": PROFILES[1].name,
            "embedding_model_revision": PROFILES[1].revision,
            "model_cache_directory": cache,
        }
    )
