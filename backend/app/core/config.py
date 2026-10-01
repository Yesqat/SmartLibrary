"""Validated process configuration. Business settings belong in PostgreSQL."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    frontend_url: str = "http://localhost:8080"
    cors_origins: list[str] = ["http://localhost:8080"]
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "backend"]
    library_timezone: str = "UTC"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    postgres_host: str = "postgres"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "smartlibrary"
    postgres_user: str = "smartlibrary"
    postgres_password: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")
    redis_host: str = "redis"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr = SecretStr("")
    redis_url: SecretStr = SecretStr("")
    jwt_secret: SecretStr = SecretStr("")
    qr_encryption_key: SecretStr = SecretStr("")
    access_token_ttl: int = Field(default=900, ge=60, le=3600)
    refresh_token_ttl: int = Field(default=2592000, ge=3600, le=7776000)
    auth_login_ip_limit: int = Field(default=30, ge=1, le=10000)
    auth_login_account_limit: int = Field(default=10, ge=1, le=1000)
    auth_login_window_seconds: int = Field(default=900, ge=1, le=3600)
    auth_register_limit: int = Field(default=10, ge=1, le=1000)
    auth_refresh_limit: int = Field(default=120, ge=1, le=10000)
    auth_rate_namespace: str = Field(default="smartlibrary:auth", pattern=r"^[a-zA-Z0-9:_-]+$")
    trust_proxy_headers: bool = False
    upload_directory: Path = Path("var/uploads")
    model_cache_directory: Path = Path("var/models")
    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    embedding_model: str = ""
    embedding_model_revision: str = ""

    @field_validator("library_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise ValueError("Use a valid IANA timezone") from None
        return value

    @model_validator(mode="after")
    def secure_configuration(self) -> Self:
        for origin in [self.frontend_url, *self.cors_origins]:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or "*" in origin:
                raise ValueError("Frontend and CORS origins must be explicit HTTP(S) origins")
            if (
                parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Origins cannot contain credentials, paths, queries or fragments")
        if not self.allowed_hosts or any("*" in host for host in self.allowed_hosts):
            raise ValueError("ALLOWED_HOSTS must be an explicit nonempty list")
        if self.database_url.get_secret_value():
            try:
                url = make_url(self.database_url.get_secret_value())
                if url.drivername != "postgresql+psycopg" or not url.host or not url.database:
                    raise ValueError
            except Exception:
                raise ValueError(
                    "DATABASE_URL requires postgresql+psycopg, host and database"
                ) from None
            db_password = url.password or ""
        else:
            db_password = self.postgres_password.get_secret_value()
        if self.redis_url.get_secret_value():
            url_redis = urlsplit(self.redis_url.get_secret_value())
            if url_redis.scheme not in {"redis", "rediss"} or not url_redis.hostname:
                raise ValueError("REDIS_URL must use redis or rediss with a host")
            redis_password = url_redis.password or ""
        else:
            redis_password = self.redis_password.get_secret_value()
        for value in (db_password, redis_password):
            if len(value) < 16 or value.lower().startswith(("change", "example", "replace")):
                raise ValueError(
                    "Configure non-default database and Redis passwords (16+ characters)"
                )
        auth_secret = self.jwt_secret.get_secret_value()
        if len(auth_secret) < 32 or auth_secret.lower().startswith(
            ("change", "example", "replace")
        ):
            raise ValueError("Configure a non-default JWT_SECRET (32+ characters)")
        if self.app_env == "production":
            if any(not o.startswith("https://") for o in [self.frontend_url, *self.cors_origins]):
                raise ValueError("Production browser origins require HTTPS")
            for credential in (self.jwt_secret, self.qr_encryption_key):
                value = credential.get_secret_value()
                if len(value) < 32 or value.lower().startswith(("change", "example", "replace")):
                    raise ValueError("Production requires non-default auth/QR secrets")
            if self.jwt_secret == self.qr_encryption_key:
                raise ValueError("Auth and QR secrets must be independent")
            try:
                Fernet(self.qr_encryption_key.get_secret_value().encode())
            except (ValueError, TypeError):
                raise ValueError("Production QR_ENCRYPTION_KEY must be a Fernet key") from None
            if self.log_level == "DEBUG":
                raise ValueError("Production debug logging is disabled")
        return self

    @property
    def database_dsn(self) -> str:
        if self.database_url.get_secret_value():
            return self.database_url.get_secret_value()
        return (
            f"postgresql+psycopg://{quote(self.postgres_user, safe='')}:"
            f"{quote(self.postgres_password.get_secret_value(), safe='')}@"
            f"{self.postgres_host}:{self.postgres_port}/{quote(self.postgres_db, safe='')}"
        )

    @property
    def redis_dsn(self) -> str:
        if self.redis_url.get_secret_value():
            return self.redis_url.get_secret_value()
        password = quote(self.redis_password.get_secret_value(), safe="")
        return f"redis://:{password}@{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
