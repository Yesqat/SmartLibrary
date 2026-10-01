"""Short-lived verification receipt bound to reservation assignment and Librarian session."""

from datetime import datetime, timedelta
from uuid import UUID

import jwt

from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import ISSUER, keyed_digest, now

AUDIENCE = "smartlibrary-pickup-confirmation"


def proof_key(settings: Settings) -> str:
    return keyed_digest(settings, "pickup-receipt-key", "v1")


def sign_proof(
    settings: Settings,
    principal: Principal,
    reservation_id: UUID,
    reader_id: UUID,
    copy_id: UUID,
    expires_at: datetime,
) -> tuple[str, datetime]:
    at = now()
    deadline = min(expires_at, at + timedelta(minutes=10))
    token = jwt.encode(
        {
            "sub": str(principal.user.id),
            "sid": str(principal.family_id),
            "rid": str(reservation_id),
            "reader": str(reader_id),
            "copy": str(copy_id),
            "type": "pickup-confirmation",
            "iat": at,
            "nbf": at,
            "exp": deadline,
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        proof_key(settings),
        algorithm="HS256",
    )
    return token, deadline


def decode_proof(
    settings: Settings, principal: Principal, reservation_id: UUID, token: str
) -> tuple[UUID, UUID]:
    try:
        data = jwt.decode(
            token,
            proof_key(settings),
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": [
                    "sub",
                    "sid",
                    "rid",
                    "reader",
                    "copy",
                    "type",
                    "iat",
                    "nbf",
                    "exp",
                    "iss",
                    "aud",
                ]
            },
        )
        if (
            data["type"] != "pickup-confirmation"
            or UUID(data["sub"]) != principal.user.id
            or UUID(data["sid"]) != principal.family_id
            or UUID(data["rid"]) != reservation_id
        ):
            raise ValueError
        return UUID(data["reader"]), UUID(data["copy"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError, KeyError):
        raise AppError("PICKUP_VERIFICATION_REQUIRED", "Броньді қайта тексеріңіз.", 409) from None
