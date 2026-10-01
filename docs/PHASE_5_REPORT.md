# PHASE 5 — Standard/fuzzy search, filters and events

Status: **PHASE 5 COMPLETE — PROCEEDING TO PHASE 6**. Verified 2026-09-27.

## 1. Implemented

Real SQL search over title, ISBN, authors, categories, publishers and description;
pg_trgm typo retrieval; bounded autocomplete; combined filters; seven sorts;
stable pagination; live physical availability; persisted search/click events.
Exact ISBN/title matches stay above weak matches, including secondary sorts.
Public catalog/home UI uses the search APIs. SEARCH.md defines ranking, metric
semantics, limits, query plans and current limitations. Semantic/Hybrid remain
PHASE 12 and are not simulated.

## 2. Files created

Backend `app/schemas/search.py`, `app/repositories/search.py`,
`app/services/search/service.py`, `app/api/v1/routes/search.py`,
`app/tests/database/domain/test_search.py`. Frontend `locales/search.ts`,
`features/catalog/search-{api.ts,input.tsx,filters.tsx,catalog.tsx}`,
`tests/search.test.tsx`. Browser `tests/e2e/search.spec.ts`.
Documentation `docs/SEARCH.md`, this report. Ignored query-plan diagnostic/logs.

## 3. Files modified

Backend main router and public single-reference reads in taxonomy routes.
Public home/catalog routes, BookCard metadata/click callback, centralized safe
error mapping, OpenAPI and generated TypeScript. Development Compose adds
WATCHPACK_POLLING=1000 and WATCHFILES_FORCE_POLLING=true for Windows bind mounts.
Affected API/catalog/deployment/testing/coverage/plan docs were synchronized.

## 4. Database migrations

None required. Existing trigram, ISBN, relation and copy indexes are reused.
Original schema remains at 0003_defaults_and_guards. Isolated fresh migration
round trips and model drift checks passed; development data was not reset.

## 5. API changes

GET `/api/v1/search`; GET `/api/v1/search/autocomplete`;
POST `/api/v1/search/{search_event_id}/click`; GET individual author/category/
publisher records for bounded URL-filter restoration. Filters reject invalid
ranges, sorts and identifiers. Search returns the existing safe Book DTO/page
plus search_event_id. Clicks require the authenticated Reader to own the search
event and the target book to have appeared in its stored bounded result list.
Retry event UUIDs deduplicate clicks. Standard errors remain centralized.

## 6. Frontend

Catalog query/filter/sort/page state is stored in the URL. Reference filters load
real labels by ID. Autocomplete debounces by 250 ms and cancels stale requests.
Book/author suggestions navigate to real detail/search contexts. Result count,
loading/empty/error/retry states and current availability are visible. Cards now
also display language/year/category. Existing staff editors are preserved.

## 7. Tests added

15 PostgreSQL cases covering exact/ISBN/fuzzy priority, English/Kazakh typos,
related metadata, combined filters, six invalid filter variants, year/title
sorts and pagination, actual borrowing popularity, autocomplete bounds/archive,
event ownership/deduplication/zero results, literal wildcard/SQL input handling,
reference lookup and five-query retrieval bound. Five frontend tests cover URL
requests, filter preservation/reset, suggestions, actual debounce, and restored
reference labels. Two browser workflows exercise real search/filter/autocomplete.

## 8. Commands actually executed

```text
backend/.venv/Scripts/ruff.exe format app                  (backend)
backend/.venv/Scripts/ruff.exe check app [--fix]            (backend)
backend/.venv/Scripts/ruff.exe format --check app           (backend)
backend/.venv/Scripts/mypy.exe app                         (backend)
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<search/catalog targets> database-tests
Get-Content -Raw work/inspect_phase5_plan.py | docker compose exec -T backend python -
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate                                     (frontend)
npx prettier --write <changed frontend/test paths>         (frontend)
npx vitest run tests/search.test.tsx tests/catalog.test.tsx
npm test; npm run lint; npm run typecheck; npm run format:check
npm run build                                            (frontend)
npx playwright test search.spec.ts --workers=1             (frontend, Edge)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps backend frontend
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose ps --format '{{.Service}} {{.Health}}'
```

Also re-read search/catalog/security/analytics requirements and prior code,
inspected installed watcher configuration, performed a live search HTTP probe,
and rechecked the specification SHA-256. Privileged operations used approved
escalation; no secret was printed.

## 9. Actual results

- First targeted PostgreSQL search run: 14 passed.
- Consolidated search plus affected catalog: **40 passed**, zero skips, 31.23 s.
- Exact-match pinning follow-up: **2 passed, 13 deselected**, 5.24 s. This is a
  targeted rerun after the sorting fix, not another full database-suite claim.
- Fresh isolated upgrade/downgrade/upgrade and Alembic drift checks passed.
- Ruff/format and mypy passed; 93 Python files, 79 typed source files.
- Frontend targeted search/catalog: ten passed; after the extra debounce test,
  complete frontend suite: **26 passed**. ESLint/TypeScript/Prettier passed.
- Native production frontend build passed; no Docker image rebuild was needed.
- Final browser: **2 passed**, 12.3 s. Initial stale-source attempts failed and
  are retained separately. No valid assertion was removed.
- Both Compose configurations valid; final six services healthy.
- Actual PostgreSQL EXPLAIN ANALYZE/BUFFERS recorded; SEARCH.md reports measured
  fixture-specific results without claiming general production performance.
- OpenAPI export/check and frontend generation passed; specification unchanged.

Evidence: `work/logs/phase5-targeted-search.txt`, `phase5-final-database.txt`,
`phase5-exact-sort-regression.txt`, `phase5-query-plans.jsonl`,
`phase5-browser.txt` (failed stale-source run), `phase5-final-browser.txt`.
Static/frontend build outputs are preserved in the execution transcript.

## 10. Problems fixed

SQL expression type inference and JSON membership narrowing were corrected.
A helper named limit shadowed autocomplete's limit parameter; renamed it.
The diagnostic EXPLAIN script initially double-escaped PostgreSQL percent
operators; corrected compilation without changing working application SQL.
Reference-filter state now survives URL restoration and does not mutate props.
Exact matches were explicitly pinned under alternate sorts and verified.
Windows Docker file notifications left old UI bundles visible; development
polling and service recreation resolved browser verification. Production config,
RBAC, tests and data were not weakened.

## 11. External requirements/blockers

None for this phase. PostgreSQL/Redis remain local required services. Search has
no external LLM dependency. pg_trgm 0.3 is a documented practical baseline, not a
claim of perfect multilingual fuzzy relevance. Search events measure API
executions, not unique user sessions; pagination/refetch can add events.

## 12. Inherited evidence

PHASE 4's 159-test full PostgreSQL/Redis regression, native image/auth checks,
catalog browser operations, stack isolation and earlier production Docker builds
remain inherited where source/config behavior is unchanged. PHASE 5 reran the
affected 40 database cases, complete frontend unit suite, frontend build and new
browser flows. It did not rerun or claim the entire backend suite or every auth
browser workflow. No schema/dependency change required image or migration work.

## 13. Specification integrity

SHA-256 remains
`DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61`.
The relevant requirements and dependencies were re-opened before implementation.
No specification edit, commit, push or remote creation occurred.

## 14. Next phase

PHASE 6 may now use the verified catalog, current physical availability,
authenticated Reader identity and existing reservation/settings schema to build
transaction-safe reservations, FIFO allocation, QR credentials and cancellation.
Proceed automatically under the user authorization.
