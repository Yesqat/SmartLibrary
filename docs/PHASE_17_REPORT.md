# PHASE 17 — PDF/XLSX reports

Status: **PHASE 17 COMPLETE — PROCEEDING TO PHASE 18**. Verified 2026-09-27.

1. **Implemented:** four actual database report types in both formats, shared
   analytics definitions, safe bounded rendering/download, Cyrillic/Kazakh fonts,
   spreadsheet types/formula safety, Admin interface and audit. See REPORTS.md.
2. **Created:** schemas/reports.py; services/reports/{__init__,data,render}.py;
   routes/reports.py; assets/fonts/{NotoSans-Regular.ttf,NotoSans-Bold.ttf,LICENSE.txt,
   README.md}; native/database report tests; frontend features/reports/{api,page},
   locale, Admin page, component tests; tests/e2e/reports.spec.ts; REPORTS.md/report.
3. **Modified:** backend dependencies/lock/router, OpenAPI/generated types, centralized
   frontend API binary decoder/error mapping and its tests, Admin navigation and
   affected documentation. Existing JSON/session client behavior retained.
4. **Migrations:** none. Existing 0004 head/fresh round-trip/drift passed in test runs.
5. **API:** POST /api/v1/admin/reports, typed validated input, actual binary attachment,
   ADMIN/Origin/rate checks, live authorization recheck before release.
6. **Frontend:** /admin/reports with type/date/format, pending duplicate prevention,
   explicit download, safe errors/no-data, private blob cleanup.
7. **Tests:** ten PostgreSQL cases, four renderer cases, three report components,
   binary client test and one browser scenario. No valid test weakened or removed.
8. **Executed:** uv lock/sync; Docker build backend/database-tests; backend-only
   development restart; ruff lint/format, mypy, native pytest; targeted and combined
   database-tests; export_openapi/api:generate/check; ESLint, Prettier, TypeScript,
   Vitest/build; Playwright reports.spec.ts; verify_stack --dev; both Compose checks;
   real database export, pypdf/openpyxl parsing, Poppler rendering and seven image
   inspections; specification hash. Downloaded official Noto fonts and license.
9. **Results:** report PostgreSQL **10 passed**, 10.65 s; final report/analytics
   **15 passed**, zero skips, 22.65 s. Native **93 passed**, 4.83 s; Ruff **182 files**,
   mypy **147 sources**. Frontend **67 passed**, lint/format/type and production build
   **44 static pages**. Edge **1 passed**, 9.6 s. Eight services healthy, private
   PG/Redis, workers/Beat, routing/readiness/OpenAPI passed. Actual report rows:
   inventory 27, borrowings 10, overdue 1, reservations 16; all files reopened and
   all seven PDF pages visually passed. Dev/test images built with new libraries.
10. **Fixed:** test fixture/API field mismatches, lint/types, report download blob
    lifecycle and browser label locator. Poppler emitted optional nameToUnicode
    path warnings for Bulgarian/Greek/Thai under the Windows username; actual
    embedded-font PDF rendering succeeded and Kazakh glyphs were inspected.
    Logs: work/logs/phase17-{build,reports-database,final-database,browser,stack}.txt.
11. **External requirements:** none for reports. Live external LLM requirement is
    unchanged and does not affect exports. Large reports require narrower dates;
    limit/error is explicit, not silent data loss.
12. **Inherited:** unchanged auth/circulation/AI suites from earlier phases; analytics
    reran because reports reuse it. Runtime production image rebuild remains PHASE 21.
13. **Specification:** unchanged SHA256
    DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
14. **Next:** PHASE 18 completes scheduled circulation/reminders using established
    transaction-safe services and existing Celery/Redis/Beat infrastructure.
