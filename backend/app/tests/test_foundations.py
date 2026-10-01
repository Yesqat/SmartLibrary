import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_liveness_does_not_require_llm_or_database(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["x-request-id"]
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_readiness_reports_failure_safely(settings, monkeypatch):
    monkeypatch.setattr("app.services.health.check_postgres", lambda engine: False)
    monkeypatch.setattr("app.services.health.check_redis", lambda client: True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {
            "status": "unavailable",
            "dependencies": {"postgres": "unavailable", "redis": "ok"},
        }
        assert settings.postgres_password.get_secret_value() not in response.text


def test_readiness_success(settings, monkeypatch):
    monkeypatch.setattr("app.services.health.check_postgres", lambda engine: True)
    monkeypatch.setattr("app.services.health.check_redis", lambda client: True)
    with TestClient(create_app(settings)) as client:
        assert client.get("/ready").json()["status"] == "ready"


def test_cors_and_safe_errors(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/missing", headers={"Origin": "https://untrusted.invalid"})
        assert response.status_code == 404
        assert "access-control-allow-origin" not in response.headers
        assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "overrides",
    [
        {"cors_origins": ["*"]},
        {"allowed_hosts": ["*"]},
        {"library_timezone": "invalid/zone"},
        {"postgres_password": "short"},
        {"app_env": "production"},
        {"database_url": "sqlite:///data.db"},
        {"access_token_ttl": -1},
    ],
)
def test_invalid_configuration_rejected(settings, overrides):
    values = settings.model_dump()
    values.update(overrides)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_configuration_and_docs(settings):
    values = settings.model_dump()
    values.update(
        app_env="production",
        frontend_url="https://library.example.org",
        cors_origins=["https://library.example.org"],
        jwt_secret="a" * 48,
        qr_encryption_key=Fernet.generate_key().decode(),
    )
    with TestClient(create_app(Settings(**values))) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/health").status_code == 200
