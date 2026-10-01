"""Both actual models return existing category IDs; similarity is not probability."""

from functools import lru_cache
from pathlib import Path
from uuid import UUID

import numpy as np

from app.ai.categorization.artifact import Artifact
from app.ai.embeddings.encoder import encoder
from app.db.enums import ScoreKind

CategoryText = tuple[UUID, str, str]


@lru_cache(maxsize=4)
def category_vectors(
    name: str, revision: str, cache: Path, categories: tuple[CategoryText, ...]
) -> list[list[float]]:
    return encoder(name, revision, cache).encode(
        [f"{label}. {description}" for _, label, description in categories]
    )


def predict(
    artifact: Artifact, cache: Path, text: str, categories: tuple[CategoryText, ...], method: str
) -> list[tuple[UUID, float, ScoreKind]]:
    if not categories:
        return []
    result = []
    if method == "classical":
        probabilities = artifact.probabilities([text])[0]
        for identity, name, _ in categories:
            if name in artifact.labels:
                score = float(probabilities[artifact.labels.index(name)])
                if score >= artifact.classical_threshold:
                    result.append((identity, score, ScoreKind.PROBABILITY))
    else:
        model = encoder(artifact.embedding_model, artifact.embedding_revision, cache)
        vector = np.asarray(model.encode([text], query=True)[0])
        references = np.asarray(
            category_vectors(
                artifact.embedding_model, artifact.embedding_revision, cache, categories
            )
        )
        similarities = references @ vector
        for (identity, _, _), score in zip(categories, similarities, strict=True):
            value = float(np.clip(score, -1, 1))
            if value >= artifact.embedding_threshold:
                result.append((identity, value, ScoreKind.COSINE_SIMILARITY))
    return sorted(result, key=lambda row: (-row[1], row[0]))[:30]
