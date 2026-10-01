# Multilingual embeddings and hybrid search

PHASE 12 implements local multilingual inference, real pgvector retrieval and
automatic metadata indexing. An external LLM is not involved.

## Selected model and measured evidence

The selected model is `intfloat/multilingual-e5-base`, immutable revision
`d128750597153bb5987e10b1c3493a34e5a4502a`, 768 dimensions. The comparison candidate
was `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions. Both support the
Kazakh/Russian/English use case. CPU inference uses normalized vectors, model-defined
pooling, `query: ` / `passage: ` prefixes and a 512-token limit. Long descriptions
are truncated; this is a retrieval limitation. Pinned safetensors are loaded locally;
remote model code and request-time downloads are disabled.

Sources: [E5 base model card](https://huggingface.co/intfloat/multilingual-e5-base),
[E5 small model card](https://huggingface.co/intfloat/multilingual-e5-small).

`ml/data/search_queries.json` contains 36 authored queries over the 12 curated seed
titles: 18 validation and 18 held-out test queries, six per language per split.
The concepts are split; the retrieval corpus is shared, as in ordinary retrieval
evaluation. No encoder training was performed. Selection uses validation MRR,
with CPU time only a tie-breaker; test results do not select the model.

| Candidate | Validation MRR | Validation recall@1 | Test MRR | Test recall@1 | Test recall@3 |
|---|---:|---:|---:|---:|---:|
| E5 small | 0.944444 | 0.888889 | 0.921296 | 0.888889 | 0.944444 |
| E5 base | 0.972222 | 0.944444 | 1.000000 | 1.000000 | 1.000000 |

Base test recall@1 was 6/6 for each language. This small, authored, seed-derived
benchmark proves these examples work; it does **not** establish production search
quality or general language accuracy. Add independent real-user judgments before
making broader claims. Actual per-query ranks, dependency versions, timing, dataset
hash and revisions are in `ml/evaluation/search_results.json`. Two actual runs
produced the same ranking metrics. CPU timings vary with load and exclude web latency.

## Index lifecycle

`bibliography-v1` uses NFC/whitespace-normalized title, sorted authors/categories,
language, year, publisher and description. Inventory, availability, cover and page
count do not affect vectors. The SHA-256 includes the recipe version.

Relevant book/reference edits delete affected vectors in the metadata transaction.
After commit a small Celery message wakes the dedicated `ml` worker. Beat sweeps
missing selected-model vectors every 60 seconds, recovering broker downtime or
interrupted jobs. Missing vectors are the durable pending state. Generation skips
unchanged hashes, runs inference outside database locks, then locks/re-reads the
book and references before publishing. A stale snapshot is rejected. Concurrent
jobs converge through the existing unique book/model constraint and guarded upsert.
Archived books never enter public retrieval. Historical model provenance is immutable.

The default worker remains separate from the single-process ML worker. Both and
Beat run in Compose; Beat health checks a recently updated scheduler heartbeat.
Circulation/reminder schedules are implemented in BACKGROUND_JOBS.md.

## Query behavior

`GET /api/v1/search?mode=standard|semantic|hybrid` shares validated filters,
pagination, sorting and current copy aggregation. Dedicated `/search/semantic`
and `/search/hybrid` aliases are also available. Empty queries browse normally.
Semantic ranking uses PostgreSQL cosine distance in the selected model space.
Filters apply before ranking. All filtered indexed titles are eligible; there is
no unvalidated similarity cutoff or claim that every low-ranked result is relevant.

Hybrid joins lexical and vector ranks in SQL and sums `1 / (60 + rank)` for each
present ranking. The smoothing value 60 follows the published baseline in
[Cormack et al., SIGIR 2009](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf);
it is not a tuned accuracy claim. Exact ISBN/title matches remain pinned first.
Lexical matches without vectors can appear while indexing. `indexing_pending`
explicitly signals missing selected-model vectors for the filters.

Availability always comes from current BOOK_COPY state. Existing SQL aggregation,
select-in relationships and bounded pagination avoid per-card queries or full
catalog transfer. Exact distance scanning is appropriate for this small corpus;
no approximate index is claimed. An actual 18-title distance plan used the model
B-tree index and completed in 0.462 ms (planning 0.366 ms), one diagnostic run,
not an endpoint benchmark. See `work/logs/phase12-vector-plan.txt`. Reassess a
model-specific HNSW index with larger representative data and measured recall.

Search executions/clicks retain STANDARD/SEMANTIC/HYBRID attribution and ownership.
Vector modes additionally allow 30 requests/IP/minute. Missing/unconfigured models
return `SEMANTIC_SEARCH_UNAVAILABLE` safely; standard search remains usable.

## Reproduce and operate

Set the selected model and immutable revision in private `.env` (see `.env.example`).
Download requires internet access to public Hugging Face model files. Inference
does not. Preserve TLS verification; corporate interception requires the trusted
system/corporate CA bundle, not disabling certificate checks.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend python -m app.ai.embeddings.cli download
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend python -m app.ai.embeddings.cli generate
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d ml-worker beat
$env:HF_HOME='C:/SmartLibrary/work/model-cache'
backend/.venv/Scripts/python.exe ml/evaluation/benchmark_search.py --download
# Repeat without --download to use the local cache.
```

The generation command also accepts `--book UUID`. Model files reside in the
persistent model volume; Windows evaluation uses `work/model-cache`. No model
weights belong in Git. For a new model, add/review an immutable encoder profile,
evaluate it, download its weights and generate its separate model/version/recipe
space before selecting it for live requests. Preserve the previous space for
rollback. Dimension/space constraints prohibit mixing vectors; metadata changes
invalidate all affected spaces. Do not overwrite provenance or silently change
the source recipe. Final executed AI/deployment evidence is recorded in PHASE_22_REPORT.md.
