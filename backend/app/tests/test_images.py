from io import BytesIO

import pytest
from PIL import Image

from app.core.errors import AppError
from app.services.storage.images import LocalImageStorage, validate_image


def encoded(format="PNG", size=(80, 100)):
    stream = BytesIO()
    Image.new("RGB", size, "red").save(stream, format)
    return stream.getvalue()


@pytest.mark.parametrize(
    "format,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_allowed_images_are_decoded_and_reencoded(format, mime):
    output = validate_image(encoded(format), mime)
    with Image.open(BytesIO(output)) as image:
        assert image.format == "WEBP" and image.size == (80, 100)
        assert not image.getexif()


@pytest.mark.parametrize("data", [encoded()[:40], encoded(size=(1, 1)), encoded(size=(6001, 16))])
def test_bad_image_dimensions_or_truncation(data):
    with pytest.raises(AppError) as error:
        validate_image(data, "image/png")
    assert error.value.code == "INVALID_IMAGE"


def test_animated_images_rejected():
    stream = BytesIO()
    first = Image.new("RGB", (30, 30), "red")
    first.save(stream, "WEBP", save_all=True, append_images=[Image.new("RGB", (30, 30), "blue")])
    with pytest.raises(AppError):
        validate_image(stream.getvalue(), "image/webp")


def test_storage_generated_names_and_safe_deletion(tmp_path):
    storage = LocalImageStorage(tmp_path)
    url = storage.save(validate_image(encoded(), "image/png"))
    assert storage.path(url.rsplit("/", 1)[1]).is_file()
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("preserve")
    storage.delete("/api/v1/media/keep.txt")
    storage.delete("/default-cover.webp")
    assert unrelated.exists()
    with pytest.raises(AppError):
        storage.path("../outside.webp")
    storage.delete(url)
    assert not storage.path(url.rsplit("/", 1)[1]).exists()
