import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai.categorization.artifact import load
from app.ai.categorization.training import Dataset, Sample, train
from app.core.errors import AppError


def test_input_excludes_training_labels():
    sample = Sample(
        id="one",
        title="A title",
        description="An original description",
        authors=["Author"],
        language="kk",
        labels=["PrivateLabelMarker"],
    )
    assert "PrivateLabelMarker" not in sample.text()
    assert "Categories:" not in sample.text()


def test_duplicate_book_identity_rejected_before_fitting(settings, tmp_path):
    source = Path(__file__).resolve().parents[3] / "ml/data/categorization.json"
    data = json.loads(source.read_text("utf-8"))
    data["samples"][1]["id"] = data["samples"][0]["id"]
    with pytest.raises(ValueError, match="distinct book identities"):
        train(Dataset.model_validate(data), settings, tmp_path)
    data["samples"][0]["labels"] *= 2
    with pytest.raises(ValidationError, match="Duplicate sample labels"):
        Dataset.model_validate(data)


def test_missing_or_malformed_artifact_has_safe_unavailable(tmp_path):
    with pytest.raises(AppError, match="CATEGORIZATION_UNAVAILABLE"):
        load(tmp_path)
    target = tmp_path / "categorization"
    target.mkdir()
    (target / "model.json").write_text('{"unexpected":"payload"}', encoding="utf-8")
    with pytest.raises(AppError, match="CATEGORIZATION_UNAVAILABLE"):
        load(tmp_path)
