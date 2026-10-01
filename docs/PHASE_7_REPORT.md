# PHASE 7 — QR verification and explicit reserved issue

Status: **PHASE 7 COMPLETE — PROCEEDING TO PHASE 8**. Verified 2026-09-27.

## 1. Implemented

Librarian-only QR verification with safe preview and audit, followed by a separate
explicit issue transaction. Current Reader/session/copy/reservation/expiry,
borrowing count and overdue rules are rechecked. Issue completes reservation,
clears QR, creates borrowing, marks copy BORROWED, records interaction/audit and
commits atomically. Same-Librarian repeats return the original loan; concurrent
different Librarians cannot issue twice. CIRCULATION.md specifies the contract.

## 2. Created

Backend schemas/circulation.py, services/borrowings/{proof,service}.py,
api/v1/routes/circulation.py, tests/database/domain/test_reserved_issue.py.
Frontend features/circulation/{api.ts,pickup.tsx}, locales/circulation.ts,
app/librarian/qr/page.tsx, tests/pickup.test.tsx. Browser
tests/e2e/{library-helpers.ts,pickup.spec.ts}. docs/CIRCULATION.md and this report.

## 3. Modified

Main router/private cache headers, OpenAPI/generated types, central frontend
error map, shared/account navigation. README and API/business/security/UI/plan/
coverage/testing documentation synchronized. PHASES 0–6 foundations preserved.

## 4. Migrations

None: existing Borrowing, Reservation, BookCopy, interaction/audit tables and
partial/composite constraints support this phase. Isolated fresh migration and
drift checks passed; original three migrations remain unchanged.

## 5. API

- POST /api/v1/librarian/qr/verify, body {token}; verifies only, never issues.
- POST /api/v1/librarian/reservations/{id}/issue, body {verification_token}.

Both require current LIBRARIAN permission, Bearer authentication, allowed Origin
and Redis limits. A preview receipt is valid at most ten minutes, bound to the
Librarian session and exact reservation/Reader/copy, purpose-separated from access
tokens. It enforces the verification step without trusting browser state. All
live business checks still run at issue time. Invalid receipts return the new
stable PICKUP_VERIFICATION_REQUIRED code. Ordinary errors remain centralized.

## 6. Frontend

Real `/librarian/qr` text/scanner-input form, safe preview, explicit confirmation,
disabled pending/expired Issue control, success/due-date display and cache
invalidation. No automatic call from verification to issue. Kazakh UI. Camera
and manual reservation-number lookup remain the PHASE 10 panel task.

## 7. Tests

15 new PostgreSQL tests include verify-without-borrowing, atomic/idempotent issue,
no QR reuse, receipt/session/resource/expiry/tamper checks, access-token separation,
role/Origin restrictions, changed account/copy/reservation state, live settings,
overdue/limit rollback, same/different-Librarian races, cross-book Reader-limit
serialization, safe audit and actual Redis rate limits. Three component tests
assert explicit confirmed issue, invalid QR and expired preview. One real browser
scenario asserts READY/RESERVED and zero issue requests before confirmation,
then COMPLETED/BORROWED and one issue request afterward.

## 8. Executed commands

```text
ruff check app [--fix / --select I --fix]; ruff format [--check] app; mypy app
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<QR/issue/reservation targets> database-tests
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate; npx prettier --write <changed frontend/browser files>
npm run typecheck; npm run lint; npm run format:check
npx vitest run tests/pickup.test.tsx; npm test; npm run build
npx playwright test pickup.spec.ts --workers=1              (Edge)
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- Initial PostgreSQL issue run: **13 passed**, zero skips, 33.58 s.
- Final affected reservation/issue gate: **33 passed**, zero skips, 69.85 s.
  Isolated upgrade/downgrade/upgrade, head and drift checks passed.
- Ruff lint/format passed (106 files); mypy passed (89 source files).
- Focused components: **3 passed**; complete frontend: **35 passed**.
  ESLint, TypeScript, Prettier and production build passed.
- Real browser: **1 passed**, 13.9 s; QR verification did not issue.
- OpenAPI check and TypeScript generation passed. Specification hash unchanged.

Evidence: work/logs/phase7-issue-first.txt, phase7-final-database.txt,
phase7-browser.txt; static/frontend build outputs are in the execution transcript.

## 10. Problems resolved

Formatting/import findings were corrected. A verification receipt was added to
bind the preview to its actor/session/assignment. Borrowing-limit verification
includes a real concurrent cross-book test, avoiding an assumption that a book
lock alone protects Reader limits. No tests were weakened or skipped.

## 11. External requirements / limitations

None blocking this phase. Browser verification creates a dedicated development
title/copy/Reader and a real active borrowing. It is retained as truthful history;
PHASE 8 can process its return through the actual service. No direct SQL reset or
fake return was performed. Camera/number fallback remain PHASE 10.

## 12. Inherited evidence

PHASE 6 native backend 66 tests, affected catalog gate, backend dev/test image
builds and six-service/private-network verification remain inherited. No Docker
configuration/dependency/model change required image rebuilds. Native backend
and full database suite were not rerun/claimed; current issue/reservation logic
was tested live and current frontend was built and exercised in the browser.

## 13. Master Specification

Re-read QR/issue, session/RBAC, safe errors, transaction, settings, idempotency and
test/acceptance requirements. SHA-256 remains:
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No specification edit, commit, push or persistent database reset.

## 14. Next phase

PHASE 8 can extend the shared book/user lock discipline, borrowing eligibility
and queue service for direct issue, return, damaged/lost and inventory lookup.
Proceed under the user's standing authorization.
