import pytest

from app.core.config import Settings


@pytest.fixture
def settings():
    return Settings(
        app_env="test",
        postgres_password="test-db-credential-123456789",
        redis_password="test-redis-credential-123456789",
        jwt_secret="test-only-signing-key-never-for-deployment-123456789",
        allowed_hosts=["testserver"],
    )
