"""Reproducible real TF-IDF/OVR and E5 validation-threshold comparison."""

import argparse
import json
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from app.ai.categorization.artifact import Artifact, LinearLabel
from app.ai.categorization.source import RECIPE, digest
from app.ai.embeddings.encoder import encoder, profile
from app.ai.embeddings.source import source_text
from app.core.config import Settings


class Sample(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=20000)
    authors: list[str]
    language: str
    year: int | None = None
    labels: list[str] = Field(min_length=1)

    def text(self) -> str:
        return source_text(self.title, self.description, self.authors, [], self.language, self.year)


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: dict[str, str]
    samples: list[Sample] = Field(min_length=10)

    @model_validator(mode="after")
    def valid_taxonomy(self) -> "Dataset":
        if not 2 <= len(self.categories) <= 200:
            raise ValueError("Provide between two and 200 actual category labels")
        if any(not name.strip() or not text.strip() for name, text in self.categories.items()):
            raise ValueError("Category names and descriptions cannot be empty")
        if any(len(set(row.labels)) != len(row.labels) for row in self.samples):
            raise ValueError("Duplicate sample labels")
        return self


def metrics(truth: np.ndarray, predicted: np.ndarray, labels: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for average in ["micro", "macro"]:
        p, r, f, _ = precision_recall_fscore_support(
            truth, predicted, average=average, zero_division=0
        )
        result[average] = {"precision": float(p), "recall": float(r), "f1": float(f)}
    p, r, f, support = precision_recall_fscore_support(
        truth, predicted, average=None, zero_division=0
    )
    result["per_category"] = {
        name: {
            "precision": float(p[i]),
            "recall": float(r[i]),
            "f1": float(f[i]),
            "support": int(support[i]),
        }
        for i, name in enumerate(labels)
    }
    return result


def threshold(truth: np.ndarray, scores: np.ndarray, candidates: list[float]) -> float:
    # Optimize validation micro F1; higher threshold breaks ties (fewer suggestions).
    return max(
        candidates,
        key=lambda value: (
            metrics(truth, scores >= value, [str(i) for i in range(truth.shape[1])])["micro"]["f1"],
            value,
        ),
    )


def train(dataset: Dataset, settings: Settings, output: Path) -> Artifact:
    if len({sample.id for sample in dataset.samples}) != len(dataset.samples):
        raise ValueError("Sample IDs must be distinct book identities")
    if len({sample.title.casefold().strip() for sample in dataset.samples}) != len(dataset.samples):
        raise ValueError("Split distinct titles; do not leak editions/translations across splits")
    labels = sorted(dataset.categories)
    if any(set(sample.labels) - set(labels) for sample in dataset.samples):
        raise ValueError("Unknown dataset label")
    texts = [sample.text() for sample in dataset.samples]
    truth = MultiLabelBinarizer(classes=labels).fit_transform([s.labels for s in dataset.samples])
    order = np.random.default_rng(42).permutation(len(texts))
    holdout = max(2, len(texts) // 5)
    test, validation, training = order[:holdout], order[holdout : 2 * holdout], order[2 * holdout :]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=30000)
    train_features = vectorizer.fit_transform([texts[i] for i in training])
    baseline = OneVsRestClassifier(
        LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        baseline.fit(train_features, truth[training])
    probabilities = baseline.predict_proba(vectorizer.transform(texts))
    item = profile(settings.embedding_model, settings.embedding_model_revision)
    model = encoder(item.name, item.revision, settings.model_cache_directory)
    books = np.asarray(model.encode(texts, query=True))
    categories = np.asarray(
        model.encode([f"{name}. {dataset.categories[name]}" for name in labels])
    )
    similarities = books @ categories.T
    selected_classical = threshold(
        truth[validation], probabilities[validation], [i / 100 for i in range(5, 96, 5)]
    )
    selected_embedding = threshold(
        truth[validation],
        similarities[validation],
        sorted(set(float(v) for v in similarities[validation].ravel())),
    )
    report = {
        "seed": 42,
        "splits": {
            name: [dataset.samples[int(i)].id for i in ids]
            for name, ids in [("training", training), ("validation", validation), ("test", test)]
        },
        "training_label_counts": {
            name: int(truth[training, i].sum()) for i, name in enumerate(labels)
        },
        "training_warnings": [str(entry.message) for entry in caught],
        "tfidf_validation": metrics(
            truth[validation], probabilities[validation] >= selected_classical, labels
        ),
        "tfidf_test": metrics(truth[test], probabilities[test] >= selected_classical, labels),
        "embedding_validation": metrics(
            truth[validation], similarities[validation] >= selected_embedding, labels
        ),
        "embedding_test": metrics(truth[test], similarities[test] >= selected_embedding, labels),
        "limitation": (
            "Small curated dataset. Sparse/absent training labels and tiny holdouts cannot "
            "establish general accuracy. No test sample used to fit vocabulary/classifiers "
            "or choose thresholds."
        ),
        "libraries": {},
    }
    import importlib.metadata

    report["libraries"] = {
        name: importlib.metadata.version(name)
        for name in ["scikit-learn", "numpy", "sentence-transformers"]
    }
    classifiers = []
    for estimator in baseline.estimators_:
        if hasattr(estimator, "coef_"):
            classifiers.append(
                LinearLabel(
                    coefficients=estimator.coef_[0].tolist(),
                    intercept=float(estimator.intercept_[0]),
                )
            )
        else:
            classifiers.append(
                LinearLabel(
                    coefficients=[0.0] * len(vectorizer.vocabulary_),
                    intercept=0,
                    constant=float(estimator.y_[0]),
                )
            )
    dataset_hash = digest(dataset.model_dump())
    artifact = Artifact(
        revision=digest(
            [
                dataset_hash,
                RECIPE,
                item.revision,
                selected_classical,
                selected_embedding,
                report["libraries"],
            ]
        ),
        labels=labels,
        vocabulary=vectorizer.vocabulary_,
        idf=vectorizer.idf_.tolist(),
        classifiers=classifiers,
        classical_threshold=selected_classical,
        embedding_threshold=selected_embedding,
        embedding_model=item.name,
        embedding_revision=item.revision,
        dimension=item.dimension,
        source_recipe=RECIPE,
        dataset_sha256=dataset_hash,
        generated_at=datetime.now(UTC).isoformat(),
        metrics=report,
    )
    # Portable JSON inference must reproduce the trained sklearn probabilities.
    assert np.allclose(artifact.probabilities(texts), probabilities, atol=1e-8)
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / "model.json.tmp"
    temporary.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(output / "model.json")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metrics", type=Path, required=True)
    args = parser.parse_args()
    settings = Settings()
    dataset = Dataset.model_validate_json(args.dataset.read_text("utf-8"))
    artifact = train(
        dataset, settings, args.output or settings.model_cache_directory / "categorization"
    )
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    report = artifact.model_dump(exclude={"classifiers", "vocabulary", "idf"})
    args.metrics.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "revision": artifact.revision,
                "thresholds": [artifact.classical_threshold, artifact.embedding_threshold],
                "test": {
                    key: value for key, value in artifact.metrics.items() if key.endswith("_test")
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
