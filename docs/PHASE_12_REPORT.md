# PHASE 12 — Embeddings, semantic and hybrid search

Status: **PHASE 12 COMPLETE — PROCEEDING TO PHASE 13**. Verified 2026-09-27.

## 1. Implemented

Real pinned multilingual E5 CPU inference, model comparison, versioned source hashes,
incremental generation, metadata invalidation and stale-job protection. PostgreSQL
cosine retrieval and SQL reciprocal rank fusion preserve exact ISBN/title priority,
filters, pagination and live copy availability. Dedicated ML worker and recovery
scheduler, safe unavailable behavior, search/click attribution and Kazakh catalog UI.

## 2. Files created

backend/app/ai/embeddings/{encoder,source,pipeline,dispatch,cli,search}.py;
repositories/vector_search.py; workers/{embeddings,scheduler}.py;
tests/database/domain/test_semantic.py; ml/data/search_queries.json;
ml/evaluation/{benchmark_search.py,search_results.json}; tests/e2e/semantic.spec.ts;
docs/SEMANTIC_SEARCH.md and this report. Diagnostic files/logs stay ignored in work/.

## 3. Files modified

Backend pyproject/uv.lock, catalog service, search repository/schema/service/routes,
Celery application; Compose/runtime/dev settings, .env.example and private model
selection only; scripts/verify_stack.py. Search UI/locales/error labels/component
fixtures, OpenAPI/generated types; search browser fixture now owns an available
copy. README and affected architecture/database/API/AI/search/security/deployment/
testing/UI/plan/coverage documents synchronized. No secrets printed or committed.

## 4. Migrations

None needed. Existing immutable model provenance, model/dimension FK, nonzero-vector
checks and unique book/model pair support the selected 768-dimensional space.
No applied migration edited. Isolated fresh upgrade/downgrade/upgrade/head/drift passed.

## 5. API changes

GET search accepts mode; GET search/semantic and search/hybrid added. SearchPage
adds indexing_pending. Existing typed filters/sorts/pagination and ownership apply.
Missing model returns SEMANTIC_SEARCH_UNAVAILABLE/503. OpenAPI --check passed.

## 6. Frontend

Catalog mode selector, natural-language hint, pending-index banner and localized
unavailable state. URL/filter state and existing reusable cards/availability remain.

## 7. Tests added

Five PostgreSQL cases use actual pinned model inference: multilingual meaning,
combined filters/current copies, hybrid exact priority, pending lexical fallback,
hash/version/dimension, stale/concurrent generation, reference invalidation,
HTTP modes/event ownership/attribution and safe unavailable behavior. Component
mode/filter/pending case and browser automatic indexing/reindexing/current-copy flow.

## 8. Commands actually executed

```text
uv sync --frozen (backend/.venv/Scripts/uv.exe; workspace cache)
python ml/evaluation/benchmark_search.py --download
python ml/evaluation/benchmark_search.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend database-tests
docker compose ... up -d backend worker ml-worker beat
docker compose ... run --rm backend python -m app.ai.embeddings.cli generate  (twice)
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -v C:/SmartLibrary/work/model-cache:/models:ro -e MODEL_CACHE_DIRECTORY=/models -e HF_HUB_OFFLINE=1 -e PYTEST_ADDOPTS=<semantic/search/catalog/reservation_catalog targets> database-tests
ruff check / format --check; mypy app
pytest -q --ignore=app/tests/database --basetemp=var/test-tmp
python scripts/export_openapi.py [--check]; npm run api:generate
npm run lint; npm run typecheck; npm run format:check; npm test; npm run build
npx playwright test semantic.spec.ts search.spec.ts --workers=1
python scripts/verify_stack.py --dev
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

Additional read-only Docker logs/health, SQL vector dimensions and EXPLAIN ANALYZE
were executed. Public selected-model files were copied from the downloaded workspace
cache into the non-root Docker model volume. Exact failed browser fixture archived
through normal authorized APIs; no persistent database reset or volume deletion.

## 9. Actual results

- Multilingual benchmark reproduced: base validation MRR 0.972222 vs small 0.944444;
  selected base test recall@1 18/18. Small authored corpus limitation explicitly
  documented; no claim of broad search accuracy. Saved JSON includes per-query ranks.
- Initial real-model PostgreSQL: **5 passed**, 27.59 s. Final affected combined:
  **48 passed, zero skips**, 99.53 s, phase12-final-database.txt. Fresh migration
  round-trip/head/drift passed in the disposable database; it was then removed.
- Ruff lint/format, mypy **112 sources**, native **66 passed** (4.57 s), frontend
  **52 passed**, ESLint/Prettier/types and production build passed. Final helper/test
  formatting and OpenAPI checks passed after fixture-only fixes.
- Edge browser **3 passed**, 54.0 s, phase12-browser-final.txt. Real ML worker indexed
  a new book and updated metadata; UI reflected an unavailable physical copy.
- Backend development and database-test image builds succeeded. Eight development
  services healthy; liveness/readiness/Nginx/contracts/default+ML worker pings/Beat
  heartbeat/extensions/private ports passed (phase12-stack.txt). Both Compose configs valid.
- Development generation: **17 generated**, then **17 unchanged**. Later read-only
  inspection during browser verification: 18 stored real vectors, min/max dimension
  768, selected immutable revision. Actual cosine SQL plan execution 0.462 ms on
  18 titles; this is a diagnostic query, not an endpoint performance claim.

## 10. Problems found and fixed

Public-model TLS initially rejected the intercepted certificate chain. Using the
existing trusted Windows CA bundle resolved it without disabling verification.
New semantic fixtures initially polluted later lexical ranking; fixture archival
now isolates them. Cleanup initially used DELETE instead of the existing PATCH
archive contract; corrected. Older browser test assumed seeded availability despite
legitimate circulation; it now creates/archives its own book/copy and preserves
the same fuzzy/filter assertions. No valid tests removed, weakened or skipped.
Workspace formatting permission denials were resolved with approved escalation.

## 11. External requirements

No PHASE 13 blocker. Fresh installations need public pinned model downloads and
adequate disk/RAM; runtime inference needs no external LLM. Benchmark remains small.
Production TLS/domain/provider setup remains in its assigned later phases.

## 12. Inherited evidence

Unchanged auth/Admin/circulation/QR/Reader flows retain PHASES 3–11 evidence; they
were not all rerun here. Affected catalog/search/database paths were rerun.
Frontend runtime image and full runtime stack were not rebuilt here; development
backend/test images and current eight-service stack were actually verified.

## 13. Master Specification integrity

SHA-256 remains DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No specification edit made.

## 14. Readiness

PHASE 13 can use immutable real vectors, current catalog aggregation, existing
Reader signals/preferences and prepared impression/event tables. PHASE 12 complete.
