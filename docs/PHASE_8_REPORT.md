# PHASE 8 — Direct issue, return, damage and loss

Status: **PHASE 8 COMPLETE — PROCEEDING TO PHASE 9**. Verified 2026-09-27.

## 1. Implemented

Real Librarian direct issue, inventory-number lookup, physical return with FIFO
reassignment, damaged return and lost processing. Current account, copy, limit,
overdue and queue-fairness rules are authoritative. Durable direct-issue retries
and terminal return/lost repeats preserve historical loans. Reader borrowing
active/history and Librarian overdue/Reader-selection APIs are available.
CIRCULATION.md documents exact behavior and operational boundaries.

## 2. Created files

Backend repositories/borrowings.py, api/v1/routes/borrowings.py,
tests/database/domain/{test_circulation.py,support.py}. Frontend circulation
inventory-search, reader-picker, direct-issue and return-book components;
Librarian issue/return route wrappers; tests/physical-circulation.test.tsx.
Browser tests/e2e/physical-circulation.spec.ts and this report.

## 3. Modified files

Shared circulation schemas/service/routes, main router/private cache headers;
OpenAPI and generated TypeScript; circulation API client/localization and shared
staff navigation. Existing issue fixture now uses a redacted repr helper.
README/API/business/security/UI/testing/coverage/plan/CIRCULATION docs synchronized.

## 4. Migrations

None required. UUIDv5 of operation namespace + Librarian ID + request UUID gives
direct issue a durable deduplication identity in the existing Borrowing primary
key. Reusing a key with another Reader/copy conflicts. This avoids an ephemeral
cache without changing the verified schema. Original migrations remain intact;
isolated fresh round trips and model/head drift checks passed.

## 5. Endpoints

- POST /api/v1/librarian/borrowings: Reader/copy UUIDs and idempotency_key.
- POST /librarian/borrowings/{id}/return: inspected CopyCondition only.
- POST /librarian/borrowings/{id}/lost.
- GET /librarian/borrowings/by-inventory/{inventory_number}.
- GET /librarian/borrowings/overdue; GET /librarian/readers.
- GET /api/v1/borrowings/me/active and /me/history.

All physical writes require LIBRARIAN, live session, Origin, Redis limits and
transactional rules. Reader queries derive ownership solely from authentication.
Safe DTOs expose no auth secrets. History contains RETURNED/LOST; overdue uses
due_at even if stored status is still BORROWED.

## 6. Frontend

`/librarian/issue` and `/librarian/return`: exact inventory lookup, real bounded
Reader search, inspected condition, confirmations, pending protection, safe
errors and Kazakh results. Changing inventory input clears previous actionable
data. Success invalidates catalog/borrowing/reservation/notification views where
applicable. No Reader return controls. Reader UI integration is PHASE 9.

## 7. Tests added

19 PostgreSQL tests: direct issue/lookup/return/history, retry-key reuse/mismatch,
old retry cannot alter a later loan, FIFO, damaged/lost/terminal rules, Reader/Admin
denial, ownership, actual overdue dates, blocked/inactive Reader return, unavailable
copies, queue priority, duplicate/different-Librarian direct issue, reservation vs
issue, return vs READY cancellation, Reader search and input validation. Four
component tests; one real direct-issue/return/FIFO browser workflow. Existing tests
are retained. The fixture repr helper hides temporary test credentials on failure.

## 8. Commands actually executed

```text
ruff check app [--select I --fix]; ruff format [--check] app; mypy app
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<circulation and reservation targets> database-tests
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate; npx prettier --write <changed frontend/browser paths>
npm run typecheck; npm run lint; npm run format:check
npx vitest run tests/physical-circulation.test.tsx tests/pickup.test.tsx
npm test; npm run build
npx playwright test physical-circulation.spec.ts --workers=1 (Edge)
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- First live run: 10 passed, then one test-fixture failure. Corrected the fixture
  to use the existing create-then-maintenance API, preserving all assertions.
- Targeted follow-up: **9 passed, 10 deselected**, 26.81 s.
- Final affected PostgreSQL circulation/issue/reservation gate: **52 passed**,
  zero skips, 47.50 s. Fresh migration round trips/head/drift passed.
- Ruff lint/format: **110 files passed**; mypy: **91 source files passed**.
- Targeted frontend: **7 passed**; complete frontend: **39 passed**.
  ESLint, TypeScript, Prettier and production build passed.
- Browser: **1 passed**, 13.9 s. Real direct issue, two WAITING readers, physical
  return/history and first-waiter READY verified. Created waiters were cancelled
  and the test title archived through normal APIs after the assertions.
- OpenAPI/type generation synchronized; specification hash unchanged.

Logs: work/logs/phase8-circulation-first.txt, phase8-circulation-targeted.txt,
phase8-final-database.txt, phase8-browser.txt. Static/frontend outputs are in
the execution transcript. The initial failure log is not a passing result.

## 10. Problems fixed

Pydantic's reserved copy method name conflicted with a DTO field; renamed the
new field physical_copy before contract release. Test setup incorrectly tried
to assign status at copy creation; corrected it to the established maintenance
workflow. Temporary test fixture representations are now redacted. No valid
test was weakened, disabled or replaced by mocked business logic.

## 11. External requirements

None blocking PHASE 8. Ineligible/legacy queues are never bypassed by direct
issue; periodic eligibility reconciliation is wired in PHASE 18. All normal
copy-availability transitions already use the shared FIFO service. Historical
development/test records are retained, not deleted/reset to force tests green.

## 12. Inherited evidence

PHASE 6 native 66 tests, backend dev/test images and six-service/private-network
verification remain inherited where unchanged. No dependency/configuration/schema
change justified Docker rebuilds. PHASE 7's verify-then-confirm browser evidence
is inherited; its PostgreSQL cases were rerun in the 52-case gate. Native tests,
the complete database suite and all Docker images were not claimed newly run.

## 13. Specification integrity

Re-read PARTS 17–20, 35, 137–143, 183–184 and return/damage/loss/concurrency
acceptance requirements and their dependencies. SHA-256 remains:
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No specification edit, commit, push or persistent database reset.

## 14. Readiness

PHASE 9 can integrate Reader dashboard, favorites, notifications, owned loan
history/profile/preferences with the verified circulation APIs. Proceed under
the user's standing authorization.
