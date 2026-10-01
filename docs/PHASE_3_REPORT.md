# PHASE 3 implementation report

Date: 2026-09-27. Scope: authentication, secure sessions/tokens, backend RBAC
and frontend auth foundations. **PHASE 3 COMPLETE — READY FOR PHASE 4.**
PHASE 4 has not started and requires explicit user instruction.

## 1. What was implemented

Re-read the entire unchanged Master Specification, including PARTS 1–200 and
final instructions, with particular attention to account, security, authorization,
audit and testing requirements. Reviewed PHASES 0–2, current configuration,
models/migrations, seed accounts, API/client contracts and existing tests before
implementation. Preserved the prescribed modular-monolith architecture and
physical-library model. No catalog, circulation or administrative management
service was introduced in this phase.

- Public registration always inserts ACTIVE/READER. Strict schemas reject role,
  status, hash and other unknown fields. Names/email/phone/password are validated.
- Login uses real Argon2id verification and safe credential errors. Unknown
  accounts perform dummy verification. Correct credentials for BLOCKED/INACTIVE
  accounts are denied; current-user and refresh also enforce account state.
- Short-lived HS256 access JWTs contain minimal identity/session claims, with
  fixed algorithm, issuer, audience and expiry checks. Roles come from the current
  database row. Tokens are held only in frontend memory.
- Opaque refresh credentials use HttpOnly, Strict cookies and SHA-256 database
  hashes. Production adds Secure and cookie prefixes. User row locks serialize
  refresh/revocation/password operations. Rotation preserves an absolute family
  expiry; reuse commits family revocation before returning an error.
- Logout and owned-session revocation invalidate existing access tokens through
  live session checks. Password change verifies the current password and revokes
  all sessions atomically with the new hash and audit event.
- Reusable Principal, permission dependencies, explicit three-role capability
  map and ownership helper support future services. Session operations enforce
  ownership in their transaction. There is no implicit administrator bypass.
- All auth mutations require an allowed Origin and a cookie-bound CSRF proof.
  Redis implements atomic login/IP/account, registration, refresh and supporting
  endpoint limits. Redis failure returns 503 without bypassing limits. Nginx
  overwrites client-address headers before the backend trusts them.
- Transactional security audit records registration, login success/failure,
  logout, password changes/failures, session revocation and refresh replay.
  Payloads exclude submitted credentials and hashes. Auth responses use no-store;
  safe errors/logs omit request bodies, tokens, SQL parameters and exception text.
- Kazakh Login/Register, session restoration, protected role layouts, account
  summaries and password/session controls use real APIs. Shared refresh and Web
  Locks coordinate tabs; logout broadcasts and identity/role/status cache clearing
  prevent retained private UI state. Safe return paths reject external redirects.

Exact policies and rationale are in [AUTHENTICATION.md](AUTHENTICATION.md).
Defaults are 15-minute access tokens, a 30-day absolute session family, Argon2id
64 MiB / three iterations / parallelism four, and 12–128-character new passwords
with common/degenerate-password rejection. These are documented security choices;
business settings remain in PostgreSQL.

## 2. Files created

Paths below are relative to `C:\SmartLibrary`.

Backend:

```text
backend/app/core/security.py
backend/app/core/auth_http.py
backend/app/core/permissions.py
backend/app/core/rate_limit.py
backend/app/api/dependencies.py
backend/app/api/v1/routes/auth.py
backend/app/schemas/auth.py
backend/app/repositories/auth.py
backend/app/services/auth/service.py
backend/app/services/audit/events.py
backend/app/tests/test_auth_security.py
backend/app/tests/database/test_auth.py
```

Frontend and browser tests:

```text
frontend/features/auth/auth-provider.tsx
frontend/features/auth/auth-form.tsx
frontend/features/auth/protected.tsx
frontend/features/auth/navigation.ts
frontend/features/auth/account-summary.tsx
frontend/features/auth/security-panel.tsx
frontend/app/(public)/login/page.tsx
frontend/app/(public)/register/page.tsx
frontend/app/(reader)/layout.tsx
frontend/app/(reader)/dashboard/page.tsx
frontend/app/admin/layout.tsx
frontend/app/admin/page.tsx
frontend/app/librarian/layout.tsx
frontend/app/librarian/page.tsx
frontend/app/account/layout.tsx
frontend/app/account/security/page.tsx
frontend/tests/auth-form.test.tsx
frontend/tests/auth-session.test.ts
tests/e2e/auth.spec.ts
```

Documentation: `docs/AUTHENTICATION.md` and this report.
Ignored evidence lives under `work/logs/phase3-*.txt`; empty-form visual checks
are `work/phase3-login-desktop.png` and `work/phase3-register-mobile.png`.

## 3. Files modified and configuration

- Backend: `pyproject.toml`, `uv.lock`, `app/main.py`, `app/core/config.py`,
  `app/core/errors.py`, `app/core/logging.py`, `app/db/models/users.py`
  (docstring only), and `app/tests/conftest.py` (test-only signing secret).
- Frontend: `services/api-client.ts`, `app/providers.tsx`,
  `app/(public)/page.tsx`, `locales/kk.ts`, `types/api.generated.ts`.
- Configuration/contracts: `.env.example`, `docker-compose.yml`,
  `infra/nginx/default.conf`, `docs/openapi.json`.
- Documentation: root README; ARCHITECTURE, API_SPEC, DATABASE, SECURITY,
  UI_SITEMAP, DEPLOYMENT, TESTING, IMPLEMENTATION_PLAN, SPECIFICATION_COVERAGE;
  historical PHASE_0/1/2_REPORT addenda; frontend auth and reader/admin/librarian
  boundary READMEs. Earlier reports retain their historical results.

Added locked PyJWT 2.15.0 and email-validator 2.3.0 (dnspython 2.8.0 dependency).
Existing Argon2, PostgreSQL, Redis, frontend dependencies and infrastructure
versions were preserved. JWT_SECRET now requires at least 32 non-default
characters in every environment. No real secret was hardcoded or printed.

Added AUTH_LOGIN_IP_LIMIT=30, AUTH_LOGIN_ACCOUNT_LIMIT=10,
AUTH_LOGIN_WINDOW_SECONDS=900, AUTH_REGISTER_LIMIT=10 and
AUTH_REFRESH_LIMIT=120; typed settings also provide a Redis test namespace.
TRUST_PROXY_HEADERS defaults false for direct backend use and is explicitly
enabled behind private Nginx in Compose. The operator/test environment receives
JWT_SECRET for settings validation, and database-tests waits for healthy Redis.
No private .env credential changes were required.

Git was already initialized on main with all project files untracked and no
commit baseline. No commit, push or remote was created. The manifest above
distinguishes this phase's implementation from the existing workspace.

## 4. Database migrations added

**None required.** The existing 27-table, 16-enum schema already provides users,
refresh-session lineage and immutable audits. The three revision files remain
byte-for-byte unchanged against the saved baseline:

- `0001_extensions`
- `0002_core_schema`
- `0003_defaults_and_guards` — current development and test head

Live development Alembic check reports head and no new upgrade operations.
The complete test run creates fresh isolated databases, upgrades, checks drift,
downgrades/re-upgrades the empty database and runs the existing schema/security/
seed/concurrency suite. No development database, seed fixture or volume was reset.
Read-only final inspection found zero leftover isolated test databases and
SHA-256-length stored refresh credentials. Four uniquely labeled E2E readers
persisted as development fixtures; existing seed passwords were preserved.

## 5. API endpoints added/changed

All additions have the `/api/v1/auth` prefix:

| Method/path | Result |
|---|---|
| GET /csrf | Cookie-bound CSRF proof |
| POST /register | 201 safe ACTIVE/READER account |
| POST /login | Access token/user plus HttpOnly refresh cookie |
| POST /refresh | Rotated refresh cookie and new access token |
| POST /logout | Revoke family and clear cookie, 204 |
| GET /me | Live authenticated user allowlist |
| POST /change-password | Verify/change password and revoke all sessions, 204 |
| GET /sessions | Own active root sessions, safe metadata only |
| DELETE /sessions/{session_id} | Revoke owned root; other owner receives 404 |

Existing health/readiness routes remain compatible. OpenAPI and generated
TypeScript match; no password hash or refresh secret appears in response schemas.
See [API_SPEC.md](API_SPEC.md) for errors and request boundaries. Test-only
permission probe routes are absent from production OpenAPI/application routes.

## 6. Frontend pages/components added

`/login`, `/register`, READER `/dashboard`, LIBRARIAN `/librarian`, ADMIN `/admin`
and shared `/account/security` are functional. Role landings show actual account
data and security/logout actions. Domain dashboards remain later-phase work.
Forms have labels, confirmation, validation, pending protection and success/error
feedback. Protected layouts provide loading, retry, anonymous redirects and role
denial; backend authorization remains authoritative. Query caches are cleared
when identity, role or status changes.

Empty desktop login (1440×1000) and mobile registration (390×844 viewport)
screenshots were viewed. Text/controls were legible without clipping; the mobile
page has no horizontal overflow. No credentials were included in these captures.

## 7. Tests added

- **46 native security cases:** Argon2id, password validation, registration
  allowlists, minimal JWT claims/expiry/issuer/audience/type, permission matrix,
  ownership and production cookie flags.
- **26 real PostgreSQL/Redis auth cases:** registration/login/current user,
  credential errors, blocked/inactive accounts, live role changes, invalid/expired
  JWTs, subject/session binding and wrong signatures, rotation/reuse/expiry/logout,
  owned-session revocation, password changes, CSRF, Redis limits/expiry/failure,
  spoofed forwarding headers, audit safety and rollback, concurrent refresh with
  a barrier. HTTP tests use the restricted database role. A separate isolated
  auth database preserves the earlier suite's fixed seed expectations.
- **11 frontend tests**, alongside the original four: form behavior and session
  orchestration, single-flight refresh, safe errors, no persisted tokens, delayed
  response races and return-path validation.
- **Four browser scenarios**, alongside the original three: anonymous guards;
  new reader registration/invalid+valid login/reload/concurrent tabs/role denial/
  session display/password change/cross-tab logout/relogin/logout; ADMIN layout;
  LIBRARIAN layout. Auth traces/video/screenshots are disabled to avoid secrets.

The original valid tests and assertions were retained. Failure injection and
permission probes exist only in tests; production authentication uses actual
PostgreSQL, Redis and cryptography.

## 8. Commands executed

Substantive commands (from root unless noted); Docker and restricted workspace
cache operations used approved escalation. Logs are under `work/logs`.

```powershell
docker version
docker info
docker context ls
docker compose version
# From backend, using the installed executable because bare uv was unavailable:
.venv/Scripts/uv.exe sync
.venv/Scripts/ruff.exe check .
.venv/Scripts/ruff.exe format --check .
.venv/Scripts/mypy.exe app
.venv/Scripts/pytest.exe -q
# From root:
backend/.venv/Scripts/ruff.exe check --config backend/pyproject.toml backend/app backend/alembic scripts
backend/.venv/Scripts/ruff.exe format --check --config backend/pyproject.toml backend/app backend/alembic scripts
backend/.venv/Scripts/python.exe scripts/export_openapi.py
backend/.venv/Scripts/python.exe scripts/export_openapi.py --check
backend/.venv/Scripts/python.exe scripts/export_schema_reference.py --check
# From frontend:
npm run api:generate
npm run lint
npm run typecheck
npm test -- --run
npm run format:check
npm run build
npm run test:e2e -- --workers=1
# From root:
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose --profile testing build database-tests backend frontend
docker compose run --rm database-tests
docker compose up -d --wait --wait-timeout 180
docker compose exec nginx nginx -s reload
backend/.venv/Scripts/python.exe scripts/verify_stack.py --test-outages
backend/.venv/Scripts/python.exe scripts/verify_stack.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait --wait-timeout 180
backend/.venv/Scripts/python.exe scripts/verify_stack.py --dev
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm database python -m app.db.manage check
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
git check-ignore .env backend/.venv frontend/node_modules work/logs/phase3-final-postgresql.txt
```

Also executed targeted source-mounted database tests while repairing failures,
Ruff/Prettier formatting, read-only PostgreSQL cleanup/fixture queries, generated
type hash comparison and an Edge screenshot/overflow check. E2E used installed
Edge and E2E_SEED_PASSWORD loaded privately from DEV_SEED_PASSWORD, then removed
from the command environment. No secret value is part of this report.

## 9. Actual test/build results and fixes

| Check | Executed result |
|---|---|
| Docker connectivity | CLI/server 29.8.0, Compose 5.5.1, Linux WSL2; responsive through approved escalation |
| Ruff lint/format | Passed; final scope 87 Python files |
| mypy | Passed, 67 source files |
| Native pytest | 59 passed, 67 explicitly skipped because this invocation has no isolated database |
| Real PostgreSQL/Redis pytest | **126 passed, zero skips**, 8.34 seconds |
| Fresh migrations | Upgrade, downgrade/re-upgrade and model drift checks passed |
| Development migration check | `0003_defaults_and_guards (head)`; no new upgrade operations |
| Frontend ESLint/TypeScript/Prettier | Passed |
| Frontend Vitest | **15 passed**, four files |
| Native frontend production build | Passed; auth routes compiled |
| OpenAPI/types/schema reference | Export/check/type regeneration passed with no drift |
| Both Compose configurations | Passed |
| Runtime image build/startup | Passed; backend, frontend and database-test images built; six healthy services |
| Runtime browser suite | **7 passed**, final run 12.8 seconds |
| Development build/startup | Passed; backend/frontend development targets and six healthy services |
| Development browser suite | **7 passed**, 17.9 seconds |
| Stack checks | Liveness, real readiness, frontend, Nginx, Swagger/OpenAPI, Celery, extensions and non-root processes passed |
| Dependency outage/recovery | PostgreSQL and Redis each caused readiness 503; UI/liveness stayed 200; recovery returned readiness 200 |
| Networking | PostgreSQL/Redis have no published host ports; only Nginx loopback ingress |
| Visual check | Desktop login and mobile registration inspected; mobile width assertion passed |
| Cleanup/persistence | No isolated test databases remain; development E2E readers and hashed sessions persisted |
| Documentation/ignore checks | 32 local Markdown targets across 18 documents resolve; .env, dependency directories and work logs are ignored |
| Master Specification | SHA-256 unchanged, recorded below |

Failures found and resolved during this phase:

1. Initial live run had **16 failures / 107 passes**. No-detail audit events
   serialized None as JSON null, violating the existing object constraint.
   Changed the audit writer to persist `{}`. Preserved the database constraint
   and added/retained transaction rollback verification. An intermediate targeted
   run failed while diagnosing SQLSTATE 23514; subsequent full runs passed
   123 cases, then 126 after additional auth regressions were added.
2. Redis eval typing initially produced three mypy errors. Corrected argument
   serialization and validated response shape; strict mypy now passes.
3. The first browser run had **6 passes / 1 failure** because an alert locator
   also matched Next.js's route announcer. Scoped it to the form without removing
   the error assertion. Final runtime and development runs pass all seven; a
   password-change success-message assertion was also added and passed.
4. Bare uv was unavailable on PATH; used the existing workspace executable.
   Native cache writes initially hit Windows access restrictions; approved
   escalation resolved them. No system ACL or Docker configuration was changed.

The remaining test warning is Starlette's httpx TestClient deprecation. Browser
output also warns about NO_COLOR/FORCE_COLOR. Neither caused test failure.
There is no claim of a penetration test, multi-browser matrix or HTTPS deployment.

Evidence logs include `phase3-final-postgresql.txt`, `phase3-frontend-build.txt`,
`phase3-final-build.txt`, `phase3-final-runtime-startup.txt`,
`phase3-final-runtime-stack.txt`, `phase3-runtime-stack.txt` (outages),
`phase3-final-runtime-browser.txt`, `phase3-development-build.txt`,
`phase3-development-startup.txt`, `phase3-development-stack.txt`,
`phase3-development-browser.txt` and `phase3-development-schema.txt`.
Initial failure logs are retained under the same ignored work/logs directory.

Master Specification SHA-256:
`DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61`.
All three existing migration file hashes also match the saved baseline.

## 10. Remaining issues, external requirements and next-phase readiness

No PHASE 3 implementation or environment blocker remains. The final running
configuration is development at http://localhost:8080 with all six services
healthy. Login/Register and account security are available. Existing privileged
development fixtures use private DEV_SEED_PASSWORD; public registration cannot
create privileged users. No external API key or email provider is needed here.

Public production deployment still needs a domain/certificate, HTTPS and the
hardening/deployment review assigned to PHASES 19/21. Only cookie/config behavior
was checked for production; this local HTTP stack is not a public deployment.
Older browsers without Web Locks retain single-tab refresh coordination but
may require relogin after simultaneous refresh; replay protection stays enforced.
Administrative role/status mutation must call the documented revocation policy
when implemented in its own phase. Profile editing, email reset, catalog,
circulation, AI, analytics and reporting remain in their assigned scopes.

PHASE 4 can use the existing schema, live authenticated Principal, explicit
catalog permission, ownership helper, transactional audit writer, safe errors
and generated client contracts. It must re-read relevant specification parts,
preserve BOOK/BOOK_COPY separation and enforce authorized catalog mutations.
**Stop here. PHASE 4 has not started.**
