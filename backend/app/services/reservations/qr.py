"""Opaque 256-bit credentials, hashed lookup and authenticated encryption at rest."""

import base64
import hashlib
import hmac
import secrets
from io import BytesIO

import qrcode
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.errors import AppError


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ReservationQR:
    def __init__(self, settings: Settings):
        value = settings.qr_encryption_key.get_secret_value()
        try:
            key = (value + "=" * (-len(value) % 4)).encode()
            self.cipher = Fernet(key)
            self.key_id = hashlib.sha256(base64.urlsafe_b64decode(key)).hexdigest()[:16]
        except (ValueError, TypeError):
            raise AppError(
                "QR_SERVICE_UNAVAILABLE", "QR қызметі уақытша қолжетімсіз.", 503
            ) from None

    def generate(self) -> tuple[str, str, str]:
        token = "slr1." + secrets.token_urlsafe(32)
        return digest(token), self.cipher.encrypt(token.encode()).decode(), self.key_id

    def recover(self, ciphertext: str, expected_hash: str, key_id: str) -> str:
        try:
            # The original development seed used this label with the same configured key.
            if key_id not in {self.key_id, "development-v1"}:
                raise InvalidToken
            token = self.cipher.decrypt(ciphertext.encode()).decode()
            if not hmac.compare_digest(digest(token), expected_hash):
                raise InvalidToken
            return token
        except (InvalidToken, UnicodeError, ValueError):
            raise AppError(
                "QR_SERVICE_UNAVAILABLE", "QR қызметі уақытша қолжетімсіз.", 503
            ) from None


def png_data_url(token: str) -> str:
    output = BytesIO()
    qrcode.make(token, box_size=8, border=4).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
