"""Validated JSON model coefficients; no pickle or executable artifact loading."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.errors import AppError


class LinearLabel(BaseModel):
    coefficients: list[float]
    intercept: float
    constant: float | None = None


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    revision: str = Field(pattern="^[a-f0-9]{64}$")
    labels: list[str] = Field(min_length=1, max_length=200)
    vocabulary: dict[str, int]
    idf: list[float] = Field(min_length=1, max_length=30000)
    classifiers: list[LinearLabel]
    classical_threshold: float = Field(gt=0, le=1)
    embedding_threshold: float = Field(ge=-1, le=1)
    embedding_model: str
    embedding_revision: str
    dimension: int
    source_recipe: str
    dataset_sha256: str
    generated_at: str
    metrics: dict[str, object]

    @model_validator(mode="after")
    def dimensions(self) -> "Artifact":
        size = len(self.idf)
        if (
            len(self.vocabulary) != size
            or set(self.vocabulary.values()) != set(range(size))
            or len(self.classifiers) != len(self.labels)
        ):
            raise ValueError("Invalid model dimensions")
        for classifier in self.classifiers:
            if len(classifier.coefficients) != size or classifier.constant not in {None, 0, 1}:
                raise ValueError("Invalid classifier dimensions")
            if not np.isfinite([*classifier.coefficients, classifier.intercept]).all():
                raise ValueError("Non-finite classifier")
        return self

    def probabilities(self, texts: list[str]) -> np.ndarray:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), sublinear_tf=True, vocabulary=self.vocabulary
        )
        vectorizer.idf_ = np.asarray(self.idf)
        features = vectorizer.transform(texts)
        scores = []
        for model in self.classifiers:
            if model.constant is not None:
                scores.append(np.full(len(texts), model.constant))
            else:
                logits = (
                    np.asarray(features @ np.asarray(model.coefficients)).ravel() + model.intercept
                )
                scores.append(1 / (1 + np.exp(-np.clip(logits, -700, 700))))
        return np.asarray(scores).T


@lru_cache(maxsize=2)
def _load(path: Path, modified: int) -> Artifact:
    if path.stat().st_size > 30_000_000:
        raise ValueError("Model artifact too large")
    return Artifact.model_validate(json.loads(path.read_text("utf-8")))


def load(cache: Path) -> Artifact:
    path = cache / "categorization" / "model.json"
    try:
        return _load(path, path.stat().st_mtime_ns)
    except (OSError, ValueError):
        raise AppError(
            "CATEGORIZATION_UNAVAILABLE", "Санаттау моделі әзірге қолжетімсіз.", 503
        ) from None
