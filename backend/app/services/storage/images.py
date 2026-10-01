"""Validated image storage. Database URLs never contain local filesystem paths."""

import logging
import re
import warnings
from io import BytesIO
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import AppError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000
PREFIX = "/api/v1/media/"
SAFE_NAME = re.compile(r"^[a-f0-9]{32}\.webp$")
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


def validate_image(content: bytes, mime: str | None) -> bytes:
    if len(content) > MAX_IMAGE_BYTES:
        raise AppError("UPLOAD_TOO_LARGE", "Сурет көлемі 5 МБ-тан аспауы керек.", 413)
    if not content or mime not in FORMATS:
        raise AppError("INVALID_IMAGE", "JPEG, PNG немесе WEBP суретін таңдаңыз.", 422)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as probe:
                width, height = probe.size
                if (
                    probe.format != FORMATS[mime]
                    or getattr(probe, "is_animated", False)
                    or min(width, height) < 16
                    or max(width, height) > 6000
                    or width * height > MAX_PIXELS
                ):
                    raise ValueError("Unsupported image")
                probe.verify()
            with Image.open(BytesIO(content)) as source:
                decoded = ImageOps.exif_transpose(source).convert("RGB")
                decoded.thumbnail((2400, 2400))
                output = BytesIO()
                decoded.save(output, format="WEBP", quality=88)
                return output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ):
        raise AppError(
            "INVALID_IMAGE", "Сурет жарамсыз немесе рұқсат етілмеген өлшемде.", 422
        ) from None


class ImageStorage(Protocol):
    def save(self, content: bytes) -> str: ...
    def delete(self, url: str | None) -> None: ...


class LocalImageStorage:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()

    def path(self, filename: str) -> Path:
        if not SAFE_NAME.fullmatch(filename):
            raise AppError("NOT_FOUND", "Сурет табылмады.", 404)
        path = self.directory / filename
        if path.is_symlink() or path.resolve().parent != self.directory:
            raise AppError("NOT_FOUND", "Сурет табылмады.", 404)
        return path

    def save(self, content: bytes) -> str:
        filename = uuid4().hex + ".webp"
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path(filename).open("xb") as target:
            target.write(content)
        return PREFIX + filename

    def delete(self, url: str | None) -> None:
        if url and url.startswith(PREFIX) and SAFE_NAME.fullmatch(url[len(PREFIX) :]):
            try:
                self.path(url[len(PREFIX) :]).unlink(missing_ok=True)
            except OSError:
                logging.getLogger("smartlibrary").warning("orphan_image_cleanup_pending")
