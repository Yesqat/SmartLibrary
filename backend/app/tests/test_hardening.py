import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize("key", ["b" * 43, "not-base64" * 8, "", "replace-this-key" * 4])
def test_production_rejects_nonfunctional_qr_key(settings, key):
    values = settings.model_dump()
    values.update(
        app_env="production",
        frontend_url="https://library.example.org",
        cors_origins=["https://library.example.org"],
        qr_encryption_key=key,
    )
    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_errors_do_not_echo_secret_inputs(settings):
    values = settings.model_dump()
    values.update(
        app_env="production",
        frontend_url="https://library.example.org",
        cors_origins=["https://library.example.org"],
        qr_encryption_key=Fernet.generate_key().decode(),
    )
    with TestClient(create_app(Settings(**values))) as client:
        response = client.get("/api/v1/books/not-a-uuid")
        assert response.status_code == 422
        assert response.json()["error"]["details"] is None
        assert "not-a-uuid" not in response.text
        assert "Traceback" not in response.text
        assert client.get("/docs").status_code == 404
