# PHASE 21 — Production-like deployment

Status: **PHASE 21 COMPLETE — PROCEEDING TO PHASE 22**. Verified 2026-09-28 local.

1. **Implemented:** HTTPS Compose override; TLS 1.2/1.3, HTTP→HTTPS 308, HSTS,
   canonical host, overwritten forwarding headers, 75-second upstream timeout,
   request limit, bounded logs/restart policies. Independent production setup,
   first-Admin operator command and real backup/isolated recovery tooling.
2. **Created:** docker-compose.production.yml; infra/nginx/production.conf.template;
   scripts/init_production_env.py, create_local_tls.py, verify_production.py,
   backup.py, verify_backup.py, run_tls_browser.py/.cjs; backend/app/db/bootstrap_admin.py;
   database/test_bootstrap_admin.py; tests/deployment/tls.spec.ts;
   frontend/playwright.production.config.ts; PRODUCTION_DEPLOYMENT.md,
   BACKUP_RECOVERY.md and this report. Ignored local TLS/config/backup artifacts.
3. **Modified:** local Nginx proxy headers/timeout, .env.example comments,
   Git/Docker/formatter/linter generated-artifact exclusions; README, deployment,
   security, testing, plan and coverage documentation. Existing auth/circulation intact.
4. **Migrations:** none. Fresh production-check database applied all five revisions;
   existing runtime head/drift, isolated test round-trip and restored schema passed.
5. **APIs:** no application route changes. Production docs endpoints disabled;
   Nginx upload ceiling returns the existing safe error envelope.
6. **Frontend:** existing production standalone application served over HTTPS with
   per-request CSP nonce; no UI redesign or weakened cookie/CSP policy.
7. **Tests:** PostgreSQL operator bootstrap checks weak-password rejection, refusal
   to promote an existing Reader, concurrent first-Admin creation, Argon2id and
   single audit event. Actual production TLS browser registration/session workflow.
8. **Executed:** base runtime backend/frontend build; updated backend build;
   development backend/frontend/test builds; all four Compose configuration checks;
   runtime/development/production startup; verify_stack.py --test-outages and --dev;
   production init/certificate/migrate/check, verify_production.py,
   run_tls_browser.py; backup.py/verify_backup.py; database-tests bootstrap case;
   Ruff/mypy, frontend lint/format/typecheck, git check-ignore and specification hash.
9. **Results:** runtime and development image builds/startup passed; eight healthy
   services in each tested configuration. PostgreSQL/Redis have no host ports and
   only internal data networks. Runtime dependency outage/recovery passed with
   readiness 503→200 while liveness/UI stayed 200. HTTPS chain/hostname, redirects,
   HSTS/CSP, Secure CSRF, CORS rejection, Host rejection, spoofed client-IP rejection,
   upload limit and live schema passed. Linux Chromium TLS flow **1 passed, 4.8 s**;
   PostgreSQL bootstrap **1 passed, 2.88 s**, no skips. Ruff **210 files**, mypy
   **150 sources**; frontend lint/format/types passed. Logs: work/logs/phase21-*.
10. **Recovery evidence:** real pg_dump restored into a new random database:
    34 users, 28 titles, 37 copies, 19 reservations, 10 borrowings, 277 audit rows,
    seven settings. Both uploaded-image/artifact archives read fully and passed
    hashes/path checks; extensions, Alembic drift and application-role reads passed.
    Only the newly created recovery database was dropped. Persistent data remained.
11. **Problems fixed / external boundaries:** strict Python TLS required certificate
    key identifiers/usage; fixed generated test certificates without disabling
    validation. Windows Kaspersky returned its own 499 warning for the private CA;
    the browser flow passed inside Docker, with no antivirus or OS trust changes.
    A logout assertion was corrected to allow the existing safe login `next` query.
    Read-only test mount/output conflict and generated formatter artifacts fixed.
    Public DNS/trusted certificates, off-site protected backups and external LLM
    credentials remain operator requirements; no public deployment was claimed.
12. **Inherited:** PHASE 20 complete 357 backend/70 frontend/24 Edge cases cover
    unchanged domain behavior. PHASE 22 will execute the entire final gate again.
    Final primary stack is development; separate E2E/TLS stacks are stopped with
    their volumes retained. No persistent database reset, Docker prune or Git push.
13. **Specification:** unchanged SHA256
    DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
14. **Readiness:** proceed to documentation synchronization, final code/database/
    security/AI/UI/infrastructure reviews, full regression and acceptance A–X.
