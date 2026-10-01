# PHASE 18 — Scheduled/background workflows

Status: **PHASE 18 COMPLETE — PROCEEDING TO PHASE 19**. Verified 2026-09-27.

1. **Implemented:** real expiration/FIFO, restored-eligibility reconciliation,
   due-soon/overdue/pickup notifications, durable deduplication, bounded batches,
   retry/timeouts and separate circulation/ML queues. See BACKGROUND_JOBS.md.
2. **Created:** services/notifications/scheduled.py; workers/circulation.py;
   database/domain/test_scheduled.py and test_worker_delivery.py; migration 0005;
   BACKGROUND_JOBS.md and this report.
3. **Modified:** Celery schedule, settings policy, reservation notification text,
   Admin setting label and affected architecture/database/business/testing docs.
4. **Migration:** 0005_reservation_reminder adds reservation_reminder_hours=6,
   bounded 0–8760. Actual development upgrade/head/drift passed; isolated fresh
   upgrade/downgrade/upgrade passed. No prior migration or persistent DB reset.
5. **API:** existing Admin settings exposes the seventh typed setting; no new route.
6. **Frontend:** Kazakh pickup-reminder setting label in the existing Admin form.
7. **Tests:** nine PostgreSQL job cases plus real Redis/Celery delivery and restart.
   Includes concurrent expiry, queue recovery, return race, QR failure rollback,
   dynamic settings, deduplication and bounded batch progress.
8. **Executed:** real development migrations/current/check; database-tests with
   app and Alembic mounts; Ruff lint/format, mypy, native pytest; frontend lint,
   types and Admin tests; Compose config checks; worker/Beat restart/up --wait;
   verify_stack --dev; actual Beat/worker log inspection; specification SHA256.
9. **Results:** initial combined PostgreSQL gate **87 passed**, 202.50 s. Final
   changed jobs/worker checks **10 passed**, zero skips, 19.05 s. Native **93 passed**,
   Ruff **186 files**, mypy **149 sources**. Frontend Admin **4 passed**, lint/types.
   Eight healthy services, private PostgreSQL/Redis, routing/readiness/OpenAPI,
   both worker pings and Beat passed. Actual periodic task deliveries succeeded
   after restart, with zero failed items. Logs: work/logs/phase18-*.txt.
10. **Fixed:** missing pickup-reminder setting and eligibility reconciliation;
    candidate selection excludes delivered notifications to prevent starvation.
    First stack check ran before restart health settled; --wait then verification
    passed. Existing documentation write ACL required approved escalation.
11. **External requirements:** none for in-app jobs. SMTP is not simulated.
12. **Inherited:** PHASE 17 full frontend 67 tests/build 44 pages and unchanged
    contracts/rendering; changed settings UI was checked. Development/test image
    build from PHASE 17 reused with mounted current sources; runtime build is PHASE 21.
13. **Master Specification:** unchanged SHA256
    DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
14. **Next:** PHASE 19 cross-system security hardening and negative authorization.
