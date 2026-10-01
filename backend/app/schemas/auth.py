"""Explicit allowlists prevent mass assignment and secret disclosure."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.db.enums import UserRole, UserStatus

Name = Annotated[str, Field(min_length=1, max_length=100)]
Password = Annotated[SecretStr, Field(min_length=1, max_length=128)]


def validate_new_password(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    common = {
        "password1234",
        "password12345",
        "password123456",
        "qwerty12345678",
        "123456789012",
        "1234567890123456",
        "iloveyou12345",
        "admin12345678",
    }
    if (
        len(password) < 12
        or len(password.encode()) > 512
        or len(set(password)) < 4
        or password.strip() != password
        or password.casefold() in common
        or any(ord(c) < 32 for c in password)
    ):
        raise ValueError("Use 12-128 characters and avoid common passwords")
    return value


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class LoginInput(Input):
    email: EmailStr = Field(max_length=320)
    password: Password

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class RegisterInput(LoginInput):
    first_name: Name
    last_name: Name
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ()\-\.]{7,32}$")

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value is not None and not 7 <= sum(c.isdigit() for c in value) <= 15:
            raise ValueError("Use a phone number with 7-15 digits")
        return value

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if any(ord(c) < 32 for c in value):
                raise ValueError("Invalid name")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: SecretStr) -> SecretStr:
        return validate_new_password(value)


class PasswordChangeInput(Input):
    current_password: Password
    new_password: Password

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: SecretStr) -> SecretStr:
        return validate_new_password(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    avatar_url: str | None
    role: UserRole
    status: UserStatus
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class CSRFResponse(BaseModel):
    csrf_token: str


class SessionResponse(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    current: bool


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
