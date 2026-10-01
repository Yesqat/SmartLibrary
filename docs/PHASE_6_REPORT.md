# PHASE 6 — Reservations, FIFO and private QR

Status: **PHASE 6 COMPLETE — PROCEEDING TO PHASE 7**. Verified 2026-09-27.

## 1. Implemented

Real Reader reservation creation, safe owner pagination/detail, deterministic
physical allocation, FIFO, account/overdue checks, live database settings,
cancellation, expiration transition, QR generation/recovery, audit, interactions
and deduplicated READY/EXPIRED notifications. Copy creation/repair uses the same
FIFO allocator. RESERVATIONS.md specifies contracts, locking and limitations.

## 2. Created files

Backend schemas/reservations.py, repositories/reservations.py,
services/settings/policy.py, services/reservations/{qr,service}.py,
api/v1/routes/reservations.py; tests/database/domain/test_reservations.py and
test_reservation_catalog.py. Frontend features/reservations/{api.ts,list.tsx,
detail.tsx,reserve-button.tsx}, locales/reservations.ts, tests/reservations.test.tsx,
Reader reservation list/detail route wrappers. tests/e2e/reservations.spec.ts,
docs/RESERVATIONS.md and this report.

## 3. Modified files

Backend main router/no-store handling, catalog copy service, domain test fixture,
pyproject.toml and uv.lock. Frontend BookDetail, shared catalog/account navigation,
safe login return paths, central API error mapping. OpenAPI/generated TypeScript;
README and affected API/business/security/database/architecture/UI/testing/plan/
coverage documentation. Existing working files were extended, not recreated.

## 4. Migrations

None required. Existing 27 tables, 16 enums and three migrations remain intact.
The PostgreSQL sequence, partial unique constraints, composite ownership FKs,
QR lifecycle checks, audit guards and notification dedup constraints are reused.
Isolated fresh migration round trips and Alembic drift checks passed.

## 5. API

POST /api/v1/reservations; GET /reservations/me; GET /reservations/{id};
POST /reservations/{id}/cancel; GET /reservations/{id}/qr. READER-only ownership,
Origin-checked mutations, Redis limits, safe errors and no-store responses.
No caller-selected physical copy or arbitrary user identity. QR reads never issue.

## 6. Frontend

Book reserve/queue action, protected list/detail, real queue position/status/
deadlines, explicitly revealed QR, expiry hiding, cancellation confirmation,
loading/empty/error/retry states and Kazakh labels. Query invalidation refreshes
availability. No Reader issue/return control. Mobile browser layout was checked.

## 7. Tests added

18 PostgreSQL cases: allocation/QR recovery/PNG validity/no borrowing,
WAITING, duplicates, allowlisted body, roles, Origin, ownership, pagination,
blocked/inactive accounts, FIFO/skipped ineligible users, settings/due_at,
expiration, missing-key rollback, concurrent reservations (same/different users),
concurrent cancellation, crypto tampering, catalog copy addition/repair and
unavailable/archive handling. Six frontend cases plus one real two-Reader browser
workflow. Existing tests remain intact.

## 8. Commands executed

```text
uv lock; uv sync --locked --group dev                     (backend .venv)
ruff check app [--fix]; ruff format [--check] app; mypy app
pytest -q --ignore=app/tests/database --basetemp=var/test-tmp
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend database-tests
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<reservation/catalog targets> database-tests
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps backend worker
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate; npx prettier --write <changed files>
npm run lint; npm run typecheck; npm run format:check; npm test; npm run build
npx vitest run tests/reservations.test.tsx [tests/catalog.test.tsx]
npx playwright test reservations.spec.ts --workers=1        (Edge)
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
backend/.venv/Scripts/python.exe scripts/verify_stack.py --dev
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

Initial OpenAPI export from backend cwd lacked the root environment; rerun from
the documented project root succeeded. An initial service name celery-worker
was invalid; the existing service is worker, whose recreation succeeded. Neither
failure was represented as successful verification.

## 9. Actual results

- Initial live PostgreSQL reservation run: **15 passed**, zero skips, 27.29 s.
- Final affected PostgreSQL reservation/catalog gate: **43 passed**, zero skips,
  47.35 s. Fresh isolated upgrade/downgrade/upgrade and drift checks passed.
- Native backend: **66 passed**, no database-test substitution, 2.41 s.
- Ruff lint/format: 101 files; mypy: 85 source files; both passed.
- Frontend focused reservation/catalog: **12 passed**; complete suite:
  **32 passed**. ESLint, TypeScript, Prettier and production build passed.
- Browser: **1 passed**, 26.4 s; two real Readers, READY/WAITING, private QR,
  other-owner denial, cancellation/FIFO and mobile width. Credentials/traces off.
- A final cancellation message distinguishes an expired hold; targeted frontend
  tests/type/format were rerun for that small presentation change.
- Affected backend dev/test Docker images built; six services healthy. Live
  frontend, backend liveness/readiness, Swagger/OpenAPI, Nginx, Celery ping,
  extensions, non-root processes and private database/cache networking passed.
- Both Compose configurations valid; API schema/type generation synchronized.

Evidence in ignored work/logs: phase6-backend-build.txt,
phase6-reservations-first.txt, phase6-final-database.txt, phase6-browser.txt and
phase6-final-stack.txt. Native/frontend command outputs are in the transcript.

## 10. Problems found and fixed

Type checks caught a nonexistent User archive field and an incorrect frontend
API helper import. Component matchers required their existing jest-dom adapter.
All were fixed. Terminal cancel remains idempotent after title archival. Released
copies get reassignment priority. Copy creation/repair now immediately honors
waiters. No valid test was removed, skipped, weakened or replaced by SQLite.

## 11. External requirements / later phases

No blocker. Keep the configured independent QR key backed up; deliberate rotation
must re-encrypt active credentials. PHASE 7 implements Librarian verification and
explicit issue; PHASE 8 implements return; PHASE 18 schedules the already-tested
expiration service. These future behaviors are not claimed complete here.

## 12. Inherited verification

PHASE 4's complete 159-test PostgreSQL/Redis suite and PHASE 5 search tests remain
evidence for unchanged behavior, not newly executed tests. The affected catalog
suite was rerun. Earlier production Docker/frontend and auth browser evidence is
inherited; PHASE 6 rebuilt backend dev/test images and built the native frontend,
not every runtime image. The successful browser run preceded the final catalog
queue integration, which was then verified by the 43-case database gate.

## 13. Specification integrity

Relevant reservation, queue, QR, settings, security, transaction, notification
and testing sections were re-read. SHA-256 is unchanged:
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No specification edits, commits, pushes or persistent database reset.

## 14. Readiness

PHASE 7 can reuse allocation locks, policy reads, secure lookup credentials and
reservation/copy invariants for QR verification followed by separate explicit
Librarian issue. Proceed automatically under the user's authorization.
