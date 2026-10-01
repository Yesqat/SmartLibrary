"""Local, revision-pinned multilingual inference; never downloads during API requests."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Any, cast

from app.core.errors import AppError


@dataclass(frozen=True)
class ModelProfile:
    name: str
    revision: str
    dimension: int
    query_prefix: str = "query: "
    passage_prefix: str = "passage: "
    max_tokens: int = 512


PROFILES = (
    ModelProfile("intfloat/multilingual-e5-small", "614241f622f53c4eeff9890bdc4f31cfecc418b3", 384),
    ModelProfile("intfloat/multilingual-e5-base", "d128750597153bb5987e10b1c3493a34e5a4502a", 768),
)


def profile(name: str, revision: str) -> ModelProfile:
    for item in PROFILES:
        if (item.name, item.revision) == (name, revision):
            return item
    raise AppError("SEMANTIC_SEARCH_UNAVAILABLE", "Мағыналық іздеу әзірге қолжетімсіз.", 503)


def download(item: ModelProfile, cache: Path) -> None:
    from huggingface_hub import snapshot_download

    if not re.fullmatch(r"[a-f0-9]{40}", item.revision):
        raise ValueError("An immutable model revision is required")
    snapshot_download(
        item.name,
        revision=item.revision,
        cache_dir=str(cache / "hub"),
        allow_patterns=["*.json", "*.txt", "*.safetensors", "*.model"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )


class Encoder:
    def __init__(self, item: ModelProfile, cache: Path):
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(2)
        self.profile = item
        self.lock = Lock()
        self.model = SentenceTransformer(
            item.name,
            revision=item.revision,
            cache_folder=str(cache / "hub"),
            local_files_only=True,
            trust_remote_code=False,
            device="cpu",
            model_kwargs={"use_safetensors": True},
        )
        self.model.max_seq_length = item.max_tokens
        if self.model.get_sentence_embedding_dimension() != item.dimension:
            raise ValueError("Unexpected embedding dimension")

    def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        import numpy as np

        prefix = self.profile.query_prefix if query else self.profile.passage_prefix
        with self.lock:
            vectors: Any = self.model.encode(
                [prefix + text for text in texts],
                batch_size=16,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        if vectors.shape != (len(texts), self.profile.dimension) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding output")
        return cast(list[list[float]], vectors.tolist())


@lru_cache(maxsize=2)
def _encoder(name: str, revision: str, cache: Path) -> Encoder:
    return Encoder(profile(name, revision), cache)


_LOAD_LOCK = Lock()


def encoder(name: str, revision: str, cache: Path) -> Encoder:
    with _LOAD_LOCK:
        return _encoder(name, revision, cache)
