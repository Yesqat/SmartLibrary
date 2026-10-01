# PHASE 14 — Auto categorization and ML evaluation

Status: **PHASE 14 COMPLETE — PROCEEDING TO PHASE 15**. Verified 2026-09-27.

## 1. Implemented

Real TF-IDF/One-vs-Rest Logistic Regression and multilingual embedding categorization,
disjoint reproducible evaluation, safe JSON artifacts and mandatory staff review.
Only active database categories are predicted; no automatic category assignment.
See CATEGORIZATION.md for algorithms, measured limitations and review semantics.

## 2. Files created

backend/app/ai/categorization/{source,artifact,training,inference,service,__init__}.py;
schemas/categorization.py; api/v1/routes/categorization.py;
tests/test_categorization.py; tests/database/domain/test_categorization.py.
Frontend features/categorization/{api,page,review}, locales/categorization.ts,
Admin/Librarian category-predictions pages, component and E2E categorization tests.
ml/data/categorization.json; ml/evaluation/categorization_results.json;
docs/CATEGORIZATION.md and this report. Generated coefficients are ignored artifacts.

## 3. Files modified

Backend main router/no-store registration; pyproject.toml/uv.lock explicitly declare
already-installed NumPy/sklearn and sklearn typing boundary. OpenAPI/generated TS;
book editor, Admin/Librarian navigation, localized API errors. Relevant README,
AI/API/security/database/UI/deployment/testing/plan/coverage and ML documentation.

## 4. Migrations

None. Existing prediction run, prediction and final-selection tables support all
provenance/review integrity. Fresh isolated upgrade/downgrade/re-upgrade and drift
checks passed. No persistent database reset or applied migration modification.

## 5. APIs

POST /api/v1/ai/categorize; GET /ai/category-predictions and /{id}; POST /{id}/review.
Staff-only, bounded pagination/input/rates, Origin protection, safe errors.

## 6. Frontend

Working Admin/Librarian prediction lists and book-specific generation/review, two
methods, explicit confirmation, manual existing-category additions, reject all,
provenance and score-kind labels. Loading/error/empty/pending states and cache invalidation.

## 7. Tests added

Seven PostgreSQL cases: both actual methods, existing IDs, no auto-write, accepted/
modified/rejected persistence, concurrent/idempotent review, stale metadata/taxonomy,
ownership/roles, invalid input and missing artifact isolation. Three native dataset/
source/artifact tests, two component tests and one actual browser two-method review.

## 8. Commands actually executed

```text
uv lock --offline; uv sync --offline --group dev
python -m app.ai.categorization.training --dataset ml/data/categorization.json --metrics ml/evaluation/categorization_results.json
python -m app.ai.categorization.training --dataset ml/data/categorization.json --output work/categorization-reproduction --metrics work/logs/phase14-reproduced-metrics.json
docker compose ... cp <artifact> backend:/app/var/models/categorization-model.json
docker compose ... exec -T backend python -c <install artifact into categorization/model.json>
ruff check app; ruff format app; ruff format --check app; mypy app
pytest -q --ignore=app/tests/database --basetemp=var/test-tmp
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -v C:/SmartLibrary/work/model-cache:/models:ro -e MODEL_CACHE_DIRECTORY=/models -e HF_HUB_OFFLINE=1 -e PYTEST_ADDOPTS=<categorization/catalog/semantic targets> database-tests
python scripts/export_openapi.py [--check]; npm run api:generate
npx prettier --write <changed files>; npx vitest run tests/categorization.test.tsx
npm run lint; npm run typecheck; npm run format:check; npm test; npm run build
npx playwright test categorization.spec.ts --workers=1
python scripts/verify_stack.py --dev
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- Initial real PostgreSQL **6 passed**, 20.10 s; final affected gate **37 passed**,
  zero skips, 48.50 s. Isolated database cleaned up successfully.
- Ruff **156 files**, mypy **128 sources**, native **71 passed**, 4.63 s.
- Targeted components **2 passed**; full frontend **57 passed**, lint/format/types
  and production build **40 routes** passed.
- Real browser **1 passed**, 20.3 s. Both inference methods executed.
- Two training runs reproduced identical coefficients/thresholds/metrics. Twelve
  samples split 8/2/2: classical test micro F1 **0**, embedding **0.666667**.
  Only two test books; no broad accuracy claim. Full per-category metrics saved.
- Eight development services healthy; OpenAPI/current routing/readiness/private
  PG/Redis ports/non-root/extensions/worker/scheduler and both Compose checks passed.
- Evidence: work/logs/phase14-{training,training-reproduced,final-database,browser,stack}.txt.

## 10. Problems fixed

Formatting/type issues resolved. Added conservative taxonomy/source rechecks and
idempotent review concurrency tests. Probability and similarity labels remain
distinct. No valid tests weakened, skipped or removed.

## 11. External requirements

No PHASE 15 blocker. Representative labeled data is needed for credible ML quality;
current tiny evaluation and sparse-label limitations are explicit. E5 weights and
trained JSON must accompany deployment. External LLM not needed for categorization.

## 12. Inherited evidence

Unchanged auth/circulation regressions inherit earlier phases. PHASE 12 development
backend/test images already contain these dependency versions; no image rebuild
claimed. Current bind-mounted development code and native production frontend built.

## 13. Specification integrity

SHA-256 unchanged: DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.

## 14. Readiness

PHASE 15 can use existing owned conversations/messages and real read-only domain
tools. Missing external credentials must produce safe unavailability, not fake AI.
