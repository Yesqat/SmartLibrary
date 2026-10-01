# PHASE 10 — Librarian Panel

Status: **PHASE 10 COMPLETE — PROCEEDING TO PHASE 11**. Verified 2026-09-27.

## 1. Implemented

Real operational dashboard, Reader search/details/current/history, reservations,
overdue filtering/sorting and shared profile. Camera QR scanning, manual number
fallback, complete safe preview and separate explicit issue. Direct issue previews
Reader eligibility/limits/due date; return shows original dates/state and actual
post-commit copy state. Existing catalog/copy/editor functionality is preserved.

## 2. Files created

Backend schemas/librarian.py, repositories/librarian.py, routes/librarian.py,
tests/database/domain/test_librarian.py. Frontend features/librarian API/dashboard/
readers/reader-detail/reservations/overdue, camera-scanner, locales/librarian,
Librarian Reader/detail/reservation/overdue route wrappers, tests/camera.test.tsx.
tests/e2e/librarian.spec.ts; docs/LIBRARIAN.md and this report.

## 3. Files modified

Shared borrowing queries/service and circulation routes, main router; OpenAPI/
generated TypeScript. Librarian landing, catalog navigation, pickup/direct/return
components and loan overdue days. package.json/package-lock pin @zxing/browser
0.2.1. Existing pickup test extended for manual preview. Relevant README/API/
security/business/deployment/UI/testing/coverage/plan docs synchronized.

## 4. Migrations

None: existing tables, constraints, settings and audit storage suffice. Applied
migrations/models unchanged. Isolated PostgreSQL round trips and head/drift passed.

## 5. APIs

GET /api/v1/librarian/dashboard, /readers/{id}, /readers/{id}/borrowings,
/reservations; POST /reservations/verify-number. Existing Reader search adds
UUID/status; overdue adds q/minimum_days/order. Every route enforces Librarian.
Number verification shares live READY/copy/account/expiry checks and scoped
receipt with QR; no borrowing is created. Shared Redis limits and distinct audits.

## 6. Frontend

Operational dashboard with configured-timezone day counts and safe recent events;
Reader/reservation/overdue pages with bounded server data, loading/empty/error/
retry/paging. Actual camera decoding, denied/unavailable/manual fallback, track
cleanup, complete preview. Camera frames stay local. Manual path reminds staff
to check Reader identity. Existing book/copy/profile pages remain functional.
AI categorization control is completed with the real algorithm in PHASE 14.

## 7. Tests added

Nine PostgreSQL tests: manual preview-only then explicit issue/reuse rejection,
expired/blocked/cancelled failure, Reader status/limit/safe DTO, search, dashboard
real counts, overdue duration filters, own Reader history, reservations and RBAC.
Three camera-boundary component tests and one manual-preview component test.
Browser test uses actual persisted reservation QR pixels and real ZXing decoding
through a controlled MediaStream, then real verify/manual/explicit issue/database.
Only physical camera hardware is substituted, never business logic.

## 8. Executed commands

```text
npm view @zxing/browser version; npm view @zxing/browser dependencies --json
npm install --save-exact @zxing/browser@0.2.1 --cache ../work/npm-cache
ruff check app [--select I --fix]; ruff format [--check] app; mypy app
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<Librarian/QR/circulation/Reader targets> database-tests
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate; npx prettier --write <changed paths>
npx vitest run <camera/pickup/circulation/Reader tests>; npm test
npm run typecheck; npm run lint; npm run format:check; npm run build
docker compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps --wait frontend
npx playwright test librarian.spec.ts physical-circulation.spec.ts pickup.spec.ts auth.spec.ts --workers=1
backend/.venv/Scripts/python.exe scripts/verify_stack.py --dev
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- Initial DB run: 1 passed, then expired-date fixture violated hold_dates; corrected
  reserved_at/ready_at/expiry chronological ordering. Targeted rerun: **24 passed**,
  24.51 s. Final affected gate: **58 passed**, zero skips, 50.20 s, fresh migration
  round trips/head/drift passed. Logs work/logs/phase10-{librarian-first,
  librarian-targeted,final-database}.txt.
- Ruff lint **120 files**, final format check **120 files**, mypy **99 sources** passed.
  A heterogeneous SQL sort dictionary type was made explicit; fixture formatting fixed.
- Targeted components: **15 passed**; complete frontend **47 passed**; lint/type/
  format and native production build passed. Final one-prop post-issue selection lock
  received targeted circulation/type/lint/format verification; unchanged build behavior
  uses the immediately preceding successful build, not a claimed second build.
- Browser **7 passed**, 1.3 min: four authentication/routing flows, real QR camera/
  manual/explicit-issue panel workflow, direct issue/return/FIFO and QR-only preview
  regression. Log work/logs/phase10-browser.txt. New panel fixture was returned and
  archived through normal APIs; historical records retained.
- Frontend development Docker image built and started healthy. Six services healthy,
  only intended Nginx host exposure; non-root app, live/ready/OpenAPI/Nginx/Celery,
  vector/pg_trgm checks passed. Logs phase10-frontend-dev-build.txt, phase10-stack.txt.
- OpenAPI synchronized; Master Specification SHA256 unchanged.

## 10. Problems fixed

Fixture expiry dates initially violated the existing valid constraint; fixed test
setup, preserved assertion. SQL mixed-field sorting needed explicit typing.
Camera lifecycle handles late permission/unmount; Reader selection is disabled
after successful direct issue until a new inventory lookup. No tests weakened.

## 11. External requirements

Physical camera/permission and HTTPS or localhost required for actual device use.
Real decoding is verified; no claim of testing every physical camera. Manual
fallback works without camera. Scheduler/reminders and real categorization remain
their authorized owning phases. No blocker for PHASE 11.

## 12. Inherited evidence

Unchanged catalog/search/auth backend behavior uses preceding phase evidence;
PHASE 6 native suite 66 tests is inherited. This phase reran affected QR/circulation/
Reader database tests and auth browser routes. No backend/test image rebuild was
needed (no Python dependency change). Full runtime image rebuild/outage simulation
are not claimed; frontend development build and current stack were actually tested.

## 13. Master integrity

Re-read Librarian capabilities/pages, PARTS 96–104 and current circulation/security
dependencies. SHA256:
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No specification edit, git publication or persistent database reset.

## 14. Readiness

Proceed to PHASE 11 Admin management, settings and read-only audits. Preserve
distinct Admin monitoring and Librarian physical-circulation permissions.
