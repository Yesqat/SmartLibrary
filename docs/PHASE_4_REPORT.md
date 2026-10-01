# PHASE 4 — Catalog and physical inventory

Status: **PHASE 4 COMPLETE — PROCEEDING TO PHASE 5**.
Verified 2026-09-27 against the preserved PHASE 0–3 implementation.

## 1. Implemented

Real catalog/reference/copy APIs and shared Kazakh public/staff UI. BOOK remains
separate from BOOK_COPY. Availability and shelf summaries are SQL aggregates.
Validated bibliographic relationships, ISBN checksums, bounded pagination,
transactional staff authorization/audits, maintenance transitions and safe
archive/restore preserve history. Covers are decoded/validated/re-encoded,
stored under generated names and safely replaced. Reader detail-view events
derive identity from authentication and deduplicate retries.

CATALOG.md describes actual rules, lock order, image limits and operational
cleanup. Full search remains PHASE 5; circulation remains PHASES 6–8.

## 2. Files created

- Backend: `app/schemas/catalog.py`, `app/repositories/catalog.py`,
  `app/services/catalog/service.py`, `app/services/copies/state.py`,
  `app/services/storage/images.py`, `app/services/storage/cleanup.py`,
  `app/api/v1/routes/catalog.py`, `app/api/v1/routes/taxonomy.py`.
- Tests: `backend/app/tests/test_images.py`,
  `backend/app/tests/database/domain/{conftest.py,test_catalog.py}`,
  `frontend/tests/catalog.test.tsx`, `tests/e2e/catalog.spec.ts`.
- Frontend: `features/catalog/{api.ts,shared.tsx,catalog-list.tsx,book-detail.tsx,
  book-editor.tsx,copy-manager.tsx,reference-picker.tsx,reference-manager.tsx}`,
  `components/books/book-card.tsx`, `locales/catalog.ts` and twelve route wrappers
  for public catalog/detail and the two staff role areas.
- Documentation: `docs/CATALOG.md`, this report. Ignored work files include
  verification logs, public layout captures and a webpack diagnostic override.

## 3. Files modified

Backend dependencies/lockfile, main router registration, optional-principal
dependency and audit entity-type parameter (existing AUTH default preserved).
Frontend centralized client, home/account navigation, generated API types and
feature/component boundary READMEs. Development Compose now selects webpack
for the frontend watcher. Production Compose and existing Dockerfiles unchanged.
README and affected architecture/API/business/security/database/UI/deployment/
testing/coverage/implementation documentation were synchronized. OpenAPI updated.

## 4. Database migrations

None added or edited. Existing 27 tables, 16 enums and revisions
0001_extensions → 0002_core_schema → 0003_defaults_and_guards remain.
Fresh isolated upgrade/downgrade/upgrade and Alembic drift checks passed.
Persistent development data was not reset.

## 5. API endpoints

GET/POST books; GET/PATCH books/{id}; PATCH books/{id}/archive;
GET/POST books/{id}/copies; PATCH copies/{id}; PATCH copies/{id}/archive;
GET/POST authors/categories/publishers; PATCH each /{id} and /{id}/archive;
POST/DELETE books/{id}/cover; GET media/{filename}; POST books/{id}/views.
Paths have the `/api/v1` prefix. Metadata writes require MANAGE_CATALOG and
allowed Origin; copy inventory reads are staff-only; view events are Reader-only.
Safe standard errors, Pydantic allowlists, OpenAPI and generated TS agree.

## 6. Frontend pages/components

Public `/catalog`, `/books/{id}`. ADMIN and LIBRARIAN roots each have `/books`,
`/books/new`, `/books/{id}`, `/books/{id}/copies`, `/references` behind existing
protected layouts. Book Cards, covers/fallbacks, forms, backend reference pickers,
pagination, availability, confirmations, pending/error/empty/success/retry states
and query invalidation are shared. No Reader issue/return action was added.

## 7. Tests added

25 PostgreSQL catalog cases: role matrix, Origin/bearer requirements, safe
inputs and conflict errors, real relations, archive/restore dependencies,
active-history protection, copy state guards, aggregate availability and a
four-query page bound, cover lifecycle/failure preservation/unsafe uploads,
transactional audit and idempotent owned view events. Eight native image cases
exercise all allowed formats, truncation/dimensions/animation and safe paths.
Six frontend cases cover actual zero availability, search requests, empty/error/
retry, details, duplicate-save prevention and archive confirmation. Two browser
flows cover public/mobile catalog and real staff create/copy/damage/archive.

## 8. Commands actually executed

Commands below ran from the root unless a directory is specified. Repeated
targeted retries are summarized; no command is presented as executed merely
because it is documented in the specification.

```text
backend/.venv/Scripts/uv.exe sync                         (backend, UV_CACHE_DIR under work)
backend/.venv/Scripts/ruff.exe check app [--fix]          (backend)
backend/.venv/Scripts/ruff.exe format [--check] app       (backend)
backend/.venv/Scripts/mypy.exe app                       (backend)
backend/.venv/Scripts/pytest.exe -q app/tests/test_images.py
backend/.venv/Scripts/pytest.exe -q --ignore=app/tests/database --basetemp=var/test-tmp
docker compose --profile test build database-tests
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<targeted catalog/image cases> database-tests
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app database-tests
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps backend worker
docker compose restart frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --force-recreate frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f work/frontend-webpack.yml up -d --no-deps frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps frontend
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose exec -T backend python -m app.services.storage.cleanup
backend/.venv/Scripts/python.exe scripts/verify_stack.py --dev
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate                                   (frontend)
npx prettier --write <changed frontend/test paths>       (frontend)
npm run format:check; npm run lint; npm run typecheck     (frontend)
npm test; npx vitest run tests/catalog.test.tsx           (frontend)
npm run build                                          (frontend)
npx playwright test catalog.spec.ts --workers=1          (frontend, Edge)
```

Also executed read-only workspace/specification/report/model/config inspection,
Docker version/service inspection, container route/file/log diagnostics, an HTTP
route probe, Playwright desktop/mobile capture and specification/migration hashes.
Docker/native writes used approved escalation where the sandbox required it.
Browser seed credentials were read privately and never printed.

## 9. Actual results

| Check | Result |
|---|---|
| Ruff lint/format | Passed; 88 Python files formatted |
| mypy | Passed; 75 source files |
| Native backend gate | 66 passed; database directory explicitly excluded |
| Targeted catalog/image PostgreSQL run | 33 passed (25 database cases + 8 native), zero skips |
| Full real PostgreSQL/Redis regression | **159 passed, zero skips**, 38.91 seconds |
| Fresh migrations/model drift | Passed; head 0003_defaults_and_guards, no new operations |
| Frontend Vitest | **21 passed**, including all prior tests |
| ESLint, TypeScript, Prettier | Passed; final types/format rechecked after contract annotation |
| Native production frontend build | Passed; all new routes compiled |
| Docker images | Affected backend development and database-test targets built |
| Both Compose configurations | Valid |
| Final development browser | **2 passed**, 14.8 seconds |
| Stack | Six healthy services; frontend/liveness/readiness/Nginx/OpenAPI/Celery passed |
| Database/networking | vector/pg_trgm available; PostgreSQL/Redis have no host ports |
| Image cleanup CLI | Executed dry run: zero eligible orphan images, no deletion |
| Visual check | Public desktop/mobile captures inspected; mobile detail overflow assertion passed |
| Specification | SHA-256 unchanged |

Saved evidence: `work/logs/phase4-final-postgresql.txt`,
`phase4-final-browser.txt`, `phase4-final-stack.txt`; failed browser attempts are
retained separately. Public captures are `work/phase4-catalog-{desktop,mobile}.png`.
Other command results are recorded in the execution transcript.

## 10. Problems found and fixed

- SQLAlchemy inferred a common base for heterogeneous reference models; precise
  union/result types fixed strict mypy without suppressing errors.
- Component testing caught a book link name polluted by fallback artwork;
  explicit title naming fixed accessibility and the original test passed.
- Docker Turbopack dev missed new/nested routes despite readable bind mounts.
  Restart recognized top-level routes; recreation still omitted copy routes.
  A controlled webpack-dev probe returned 200 for the same nested route. The
  development Compose command now uses webpack; architecture/build command unchanged.
- Browser combobox and error locators were aligned with the actual accessible
  controls/application alert. All workflow assertions remain and pass.
- A new test needed Prettier formatting. Final format check passes.
- Native cache/OpenAPI writes required approved escalation. No system ACL,
  database reset, global Docker change or test weakening was used.

Warnings: Starlette's TestClient/httpx deprecation and Playwright color-variable
warning remain non-failing. The initial unprivileged native test also reported a
cache-write warning; the escalated native final gate passed without that warning.

## 11. External requirements/blockers

None for PHASE 4. Local image storage is operational. Object storage/public TLS
are later deployment choices. Browser-created records remain identified test
fixtures in development; successful flows archive their titles. No production
analytics or seed-derived hardcoded availability was introduced.

## 12. Inherited unchanged evidence

PHASE 3 runtime production Docker startup, dependency outage recovery, seven
auth/foundation browser flows and historical role isolation evidence are inherited
where unchanged; they were not all rerun or relabeled as new PHASE 4 evidence.
The full backend suite and frontend unit suite were actually rerun because
shared routing/audit/client/dependency code changed. PHASE 4 did not rebuild or
claim new runtime production frontend Docker verification; native production
build and the current development stack were verified.

## 13. Master Specification integrity

Read all 10,968 lines before editing, then re-opened the catalog/image/API and
dependency requirements. SHA-256 remains:
`DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61`.
No specification content was modified. No commit, push or remote was created.

## 14. Next phase

PHASE 5 can extend the bounded repository queries and generated catalog DTOs
with standard/fuzzy search, filters, ranking, autocomplete and search events.
The catalog, copy separation, role protection and existing foundations remain
available. Proceed automatically under the current user authorization.
