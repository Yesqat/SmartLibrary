# PHASE 13 — Recommendation system

Status: **PHASE 13 COMPLETE — PROCEEDING TO PHASE 14**. Verified 2026-09-27.

## 1. Implemented

Database-derived popularity, real pgvector similar books, bounded weighted personal
profiles, category/popularity fusion, cold start and prior-borrowing exclusion.
Real rendered-card impressions and owned deduplicated clicks; no fabricated CTR.
Working offline collaborative boundary/evaluator, with honest insufficient-data result.

## 2. Files created

backend/app/ai/recommendations/{__init__,policy,service,tracking,collaborative,evaluate}.py;
repositories/recommendations.py; schemas/recommendations.py;
api/v1/routes/recommendations.py; tests/database/domain/test_recommendations.py;
tests/test_collaborative.py. Frontend features/recommendations/{api,section},
locales/recommendations.ts, tests/recommendations.test.tsx;
tests/e2e/recommendations.spec.ts; ml/evaluation/recommendation_results.json;
docs/RECOMMENDATIONS.md and this report.

## 3. Files modified

Backend main route/no-store registration and shared real-model test fixture;
semantic tests use that unchanged fixture. OpenAPI/generated TS, Home/Book Details/
Reader dashboard, localized API error, relevant catalog/circulation/favorite/
reservation cache invalidation. README and affected AI/API/security/database/UI/
testing/plan/coverage docs. No dependency or Compose changes.

## 4. Migrations

None. Existing impression/click FK, unique delivery key and single-click index
provide required integrity. Isolated migration round-trip/head/drift passed;
no applied migrations or persistent database reset.

## 5. APIs

GET /api/v1/books/popular; books/{id}/similar; recommendations/me.
POST recommendations/impressions; recommendations/impressions/{id}/click.
Bounded limits, Reader identity from auth, no-store, Origin/rate protections,
30-minute signed returned-card receipts and live session/ownership checks.

## 6. Frontend

Popular Home section, similar Book Details section and personalized dashboard.
Reusable cards/explanations show live copy counts. Loading/empty/pending/error/retry
states. IntersectionObserver records 50%-visible/one-second cards or explicit clicks;
hidden/offscreen cards do not count. Telemetry failure does not block navigation.

## 7. Tests added

Six real-PostgreSQL cases cover cold start/preferences, missing model, canonical
weights/daily dedup/window, real similarity, weighted profile effects, previous-loan
exclusion with permitted repeat borrowing, live availability, concurrent impression
idempotence, click/source ownership, tampering, expiry/session binding, roles and
archival. Two native collaborative tests, three visibility/empty-state component
tests, one real browser render/click/similar/popular flow.

## 8. Executed commands

```text
ruff check app [--fix]; ruff format app; ruff format --check app; mypy app
pytest -q app/tests/test_collaborative.py --basetemp=var/test-tmp
pytest -q --ignore=app/tests/database --basetemp=var/test-tmp
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -v C:/SmartLibrary/work/model-cache:/models:ro -e MODEL_CACHE_DIRECTORY=/models -e HF_HUB_OFFLINE=1 -e PYTEST_ADDOPTS=<recommendations/semantic/reader targets> database-tests
python scripts/export_openapi.py [--check]; npm run api:generate
npx prettier --write <changed files>
npx vitest run tests/recommendations.test.tsx tests/reader.test.tsx tests/catalog.test.tsx
npm run lint; npm run typecheck; npm run format:check; npm test; npm run build
npx playwright test recommendations.spec.ts --workers=1
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m app.ai.recommendations.evaluate --output /app/var/models/recommendation-evaluation.json
docker compose ... cp backend:/app/var/models/recommendation-evaluation.json ml/evaluation/recommendation_results.json
python scripts/verify_stack.py --dev
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Results

- Initial recommendation PostgreSQL **4 passed**, 18.35 s; final affected gate
  **26 passed**, zero skips, 33.93 s (phase13-final-database.txt). Real E5 vectors
  and PostgreSQL operators executed. Fresh isolated migration/drift checks passed.
- Ruff lint/format **147 files**, mypy **121 sources**, native **68 passed**, 3.28 s.
- Targeted frontend **13 passed**; full **55 passed**, ESLint/Prettier/types and
  production frontend build passed.
- Real Edge flow **1 passed**, 6.6 s total (phase13-browser.txt).
- Eight current development services healthy; current contracts/routing/liveness/
  readiness/extensions/worker/scheduler/private ports passed (phase13-stack.txt).
- Collaborative evaluation: **0 Readers with three distinct loans**, status
  INSUFFICIENT_DATA, metrics null. No collaborative relevance claim. Real aggregate
  dataset hash and timestamp saved. Content-based serving is operational.

## 10. Problems fixed

Formatting/type issues corrected, including float collaborative scores. Shared
model fixture moved to conftest without changing its real-inference requirements.
Recommendation cache invalidation added to relevant successful mutations; catalog
copy/reference changes also invalidate search. No valid tests weakened/skipped.

## 11. External requirements

No PHASE 14 blocker. Collaborative serving needs representative multi-user loan
histories and held-out comparison before activation. External LLM is not needed
for any PHASE 13 mode. No training/model-quality accuracy fabricated.

## 12. Inherited evidence

Unchanged Docker/dependency builds and both Compose validations inherit PHASE 12.
Auth/Admin/circulation concurrency gates inherit their completed phases; selected
Reader/semantic paths were rerun. No new image build claimed; current development
bind-mounted code and frontend native production build were verified.

## 13. Specification integrity

SHA-256 unchanged: DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.

## 14. Readiness

PHASE 14 can reuse real multilingual inference and existing category review tables.
No schema or architecture rewrite required. PHASE 13 complete.
