"""Reproducible local retrieval comparison; no fabricated or provider-derived scores."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
from app.ai.embeddings.encoder import PROFILES, Encoder, download
from app.ai.embeddings.source import RECIPE, source_text
from app.db.seed_data import BOOKS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=ROOT / "work/model-cache")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    dataset = ROOT / "ml/data/search_queries.json"
    queries = json.loads(dataset.read_text(encoding="utf-8"))["queries"]
    titles = [book[0] for book in BOOKS]
    documents = [
        source_text(t, d, [a], list(c), lang, year) for t, a, lang, year, c, d in BOOKS
    ]
    results = []
    for item in PROFILES:
        if args.download:
            download(item, args.cache)
        started = perf_counter()
        model = Encoder(item, args.cache)
        passages = np.array(model.encode(documents))
        queries_start = perf_counter()
        vectors = np.array(model.encode([q["q"] for q in queries], query=True))
        query_ms = (perf_counter() - queries_start) * 1000 / len(queries)
        ordering = np.argsort(-(vectors @ passages.T), axis=1, kind="stable")
        rows = []
        for q, order in zip(queries, ordering, strict=True):
            rank = list(order).index(titles.index(q["title"])) + 1
            rows.append({**q, "rank": rank, "first": titles[order[0]]})
        metrics = {}
        for split in ["validation", "test"]:
            for language in ["all", "kk", "ru", "en"]:
                group = [
                    r
                    for r in rows
                    if r["split"] == split
                    and (language == "all" or r["language"] == language)
                ]
                metrics[f"{split}/{language}"] = {
                    "n": len(group),
                    "mrr": sum(1 / r["rank"] for r in group) / len(group),
                    "recall_at_1": sum(r["rank"] == 1 for r in group) / len(group),
                    "recall_at_3": sum(r["rank"] <= 3 for r in group) / len(group),
                }
        result = {
            "model": item.name,
            "revision": item.revision,
            "dimension": item.dimension,
            "metrics": metrics,
            "batch_query_ms_per_item": query_ms,
            "total_seconds": perf_counter() - started,
            "queries": rows,
        }
        results.append(result)
        print(
            json.dumps(
                {k: v for k, v in result.items() if k != "queries"}, ensure_ascii=False
            ),
            flush=True,
        )
        del model
    selected = max(
        results,
        key=lambda r: (
            r["metrics"]["validation/all"]["mrr"],
            -r["batch_query_ms_per_item"],
        ),
    )
    output = {
        "libraries": {
            name: importlib.metadata.version(name)
            for name in ["sentence-transformers", "torch", "transformers", "numpy"]
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "source_recipe": RECIPE,
        "selection": "Highest validation MRR; CPU query time breaks ties. Test split not used for selection.",
        "selected_model": selected["model"],
        "results": results,
        "limitation": "36 authored queries over 12 curated seed titles. Descriptions inform queries. Not an independent real-user benchmark or evidence of broad language quality.",
    }
    (ROOT / "ml/evaluation/search_results.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
