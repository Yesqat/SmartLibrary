# PHASE 16 — Database-derived analytics

Status: **PHASE 16 COMPLETE — PROCEEDING TO PHASE 17**. Verified 2026-09-27.

1. **Implemented:** six analytics groups, shared date/state definitions, SQL
   aggregation, real CTR/review/assistant measurement, zero buckets and Admin charts.
   Exact definitions and limitations: ANALYTICS.md.
2. **Created:** backend schemas/analytics.py, services/analytics/{definitions,catalog,
   circulation,ai}.py, routes/analytics.py, native date tests and database/domain/
   test_analytics.py; frontend features/analytics/{api,charts,panels,page}, locale,
   Admin analytics/AI routes, component and browser tests; ANALYTICS.md and this report.
3. **Modified:** model index declarations, router registration, OpenAPI/generated
   TS/schema reference, Admin Dashboard/navigation/locales, browser login wait for
   development compilation, README and affected architecture/API/database/security/
   UI/testing/plan/coverage documentation.
4. **Migration:** 0004_analytics_indexes, nine additive indexes. Applied to actual
   development PostgreSQL; head/drift passed. Disposable fresh chain upgrade,
   downgrade, re-upgrade and drift passed; no persistent reset.
5. **API:** GET /api/v1/admin/analytics/{overview,circulation,inventory,readers,search,ai}.
   ADMIN only, date validation, no-store, rate limit, read-only consistent snapshot.
6. **UI:** /admin/analytics and /admin/ai, plus Dashboard charts. Kazakh controls,
   Recharts, date filters, tables, truthful no-data/unknown/error states.
7. **Tests:** five real PostgreSQL cases, eight date/percentage cases, three components
   and one real Edge scenario. Existing Admin/schema tests preserved and rerun.
8. **Commands executed:** ruff check/format --check app; mypy app; native pytest
   --ignore=app/tests/database; targeted/full affected Docker database-tests with
   app/alembic mounts; database manage upgrade/check; export_openapi --check and
   api:generate; export_schema_reference; prettier, lint, format:check, typecheck,
   Vitest, production build; Playwright analytics.spec.ts; both Compose config
   --quiet; live index query and EXPLAIN ANALYZE; specification SHA-256.
9. **Results:** initial PostgreSQL **5 passed**, 7.58 s; final analytics/Admin/schema
   **30 passed**, zero skips, 25.41 s. Ruff **174 files**, mypy **142 sources**;
   native **89 passed**, 3.37 s. Frontend **63 passed**, all lint/format/type gates
   and production build **43 static pages**. Edge **1 passed**, 8.9 s. Contract and
   both Compose configurations passed. Live 144 indexes including Alembic; tiny
   ten-loan aggregate execution 0.065 ms, not a general performance claim.
10. **Fixed:** new routes placed under existing protected Admin layout; native
    temporary-directory permissions resolved with approved execution; browser wait
    increased to 15 seconds after measured 5.1-second cold page compilation. First
    log write and inline-shell query attempts failed; corrected and actually rerun.
    No valid test removed/weakened. Logs: work/logs/phase16-{analytics-database,
    final-database,browser}.txt.
11. **External requirements:** none for analytics. Live LLM configuration remains
    separately documented; analytics honestly count actual failures/successes.
12. **Inherited:** unchanged circulation/ML/auth tests and eight-service infrastructure
    baseline from earlier phases. No new Docker image build or full-stack outage test
    claimed. Actual new APIs/UI ran through current Docker/Nginx in the browser gate.
13. **Specification:** unchanged SHA-256
    DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
14. **Readiness:** PHASE 17 can reuse shared reporting periods, active/overdue predicates
    and metric services for real PDF/XLSX exports.
