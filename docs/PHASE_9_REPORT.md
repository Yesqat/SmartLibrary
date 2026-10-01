# PHASE 9 — Reader experience

Status: **PHASE 9 COMPLETE — PROCEEDING TO PHASE 10**. Verified 2026-09-27.

## 1. Implemented

Real Reader dashboard summaries/loans/reservations, favorites, notification
ownership/read/read-all, My Books/history, active/history reservation filters,
profile/avatar and optional actual category interests. READER.md defines behavior.
Reader never receives a physical-return control or permission. Existing secure
password change is linked from Profile. Email is explicitly read-only.

## 2. Files created

Backend: schemas/reader.py, repositories/reader.py, services/users/{profile,reader}.py,
api/v1/routes/reader.py, tests/database/domain/test_reader.py.
Frontend: features/reader/{api,dashboard,favorites,notifications,loans,profile},
locales/reader.ts, protected favorites/my-books/history/notifications route wrappers,
account/profile, tests/reader.test.tsx. Browser tests/e2e/reader.spec.ts.
docs/READER.md and this report.

## 3. Files modified

Backend main/private cache policy, reservation route/repository active filter,
active borrowing ordering. OpenAPI/generated TypeScript synchronized.
Frontend Reader dashboard wrapper, shared navigation, safe return routes, Book
Details favorite control, reservation API/list and affected cache invalidations.
Existing reservation component assertion updated to the new active-filter contract,
with extra history-tab assertions. README/API/UI/testing/plan/coverage synchronized.

## 4. Migrations

None. Existing favorites, notifications, preferences and User columns cover these
requirements. Models and applied migration files remain unchanged. Actual isolated
PostgreSQL upgrade/downgrade/upgrade and head/drift checks passed.

## 5. APIs

GET favorites; GET/POST/DELETE favorites/{book_id}; GET notifications;
PATCH notifications/{id}/read; POST notifications/read-all; GET reader/summary;
GET/PATCH users/me; GET/PATCH users/me/preferences; POST/DELETE users/me/avatar.
All under /api/v1. Reservation /me adds optional active filter. Reader identity
is never supplied in request data. Profile is own-account for all authenticated roles.

## 6. Frontend

Kazakhlanguage dashboard, favorites, notifications, My Books/history and Profile.
Existing reservation QR/cancel remains integrated. Loading/empty/error/retry states,
pending protection, avatar removal confirmation, safe notification navigation,
real availability and cache invalidation. Profile includes existing secure session/
password page link. Recommendations/Assistant are implemented in their owning later phases.

## 7. Tests added

15 PostgreSQL cases cover concurrent/idempotent favorites and interaction count,
availability/archived history, ownership, notifications/read-all, six mass-assignment
fields, profile persistence/validation, image-content/mime/replacement/cleanup,
atomic interests, actual overdue date, reservation tabs and staff role restrictions.
Four component tests; one actual Reader browser workflow. Existing tests preserved.

## 8. Commands actually executed

```text
ruff check app [--fix]; ruff format [--check] app; mypy app
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<Reader and affected circulation/reservation files> database-tests
backend/.venv/Scripts/python.exe scripts/export_openapi.py [--check]
npm run api:generate; npx prettier --write <changed paths>
npx vitest run tests/reader.test.tsx [tests/reservations.test.tsx]
npm test; npm run lint; npm run typecheck; npm run format:check; npm run build
npx playwright test reader.spec.ts --workers=1 (Edge)
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- First PostgreSQL Reader run: **15 passed**, zero skips, 8.57 s.
- Final affected PostgreSQL gate: **49 passed**, zero skips, 34.45 s; migration
  round trips/head/drift passed. Logs work/logs/phase9-{reader-first,final-database}.txt.
- Ruff lint/format **116 files**; mypy **96 source files** passed.
- Four new component tests passed. Initial full frontend: 42 passed, one stale
  call-signature assertion failed; strengthened for active/history contract.
  Targeted Reader/reservation rerun: 10 passed; final complete frontend **43 passed**.
- ESLint, TypeScript, Prettier, production build passed. Subsequent cache-key-only
  additions passed frontend suite/lint/type/format; build evidence inherited for
  unchanged route/dependency/build behavior, not claimed rerun after those additions.
- Browser **1 passed**, 19.6 s: favorite/list, reservation notification/read-all,
  profile persistence, My Books without return control and reservation history.
  Fixture reservation/favorite cancelled/removed and own title archived by real APIs.
  Log work/logs/phase9-browser.txt.
- OpenAPI check passed; Master Specification hash unchanged.

## 10. Problems fixed

React render-purity check rejected Date.now during render; remaining-time display
now uses initialized clock state with a cleaned-up interval. Reservation component
test now checks the new third argument and history reset. No valid test disabled,
skipped, weakened or replaced by mocked backend logic.

## 11. External requirements

None blocking this phase. Email changes/reset delivery are not advertised as working.
Optional Reader interests are ready for actual recommendation algorithms in PHASE 13.
Scheduled notifications remain PHASE 18; current READY/EXPIRED events are real.

## 12. Inherited verification

PHASE 8 circulation/QR implementation and previous explicit-issue browser evidence
remain valid. PHASE 6 native 66 tests and six-service/private-network verification
are inherited where unchanged. No dependencies/schema/Compose changes required image
rebuilds. Complete backend/all-browser/Docker rebuild suites were not newly executed.

## 13. Master integrity

Re-read Reader/favorites/notifications/preferences/API/UI/profile/upload requirements
and dependencies. SHA256 remains
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
No Master edit, commit/push or persistent database reset.

## 14. Readiness

PHASE 10 can finish Librarian operations, dashboard, Reader details/overdue views,
browser-camera scanning and manual reservation fallback on the verified domain APIs.
