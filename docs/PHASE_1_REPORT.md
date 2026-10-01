# PHASE 1 implementation report

PHASE 3 addendum: authentication/session/RBAC work was subsequently authorized
and completed. Runtime/development checks and seven browser tests per stack
passed. See PHASE_3_REPORT.md. The earlier phase evidence below is historical.

PHASE 2 addendum: the user subsequently authorized and completed the database
phase. Migrations, schema/seed/role inspection and all 54 tests passed against
the real PostgreSQL environment after storage recovery. Runtime/development
startup, six-service health and three browser checks also passed. See
PHASE_2_REPORT.md for current evidence. The PHASE 1 evidence below is historical.

Date: 2026-09-27. Scope: project structure and Docker development environment only.

Status: **PHASE 1 COMPLETE — READY FOR PHASE 2**. Final runtime and development builds, startup, integration/outage checks and browser tests passed after Docker Desktop recovered. PHASE 2 has not started and requires explicit user instruction.

The final verification resumption preserved the existing implementation. Only this report, README.md, docs/PHASE_0_REPORT.md, docs/DEPLOYMENT.md, docs/IMPLEMENTATION_PLAN.md and docs/ARCHITECTURE.md were edited. No application, test, dependency, Docker or environment configuration was changed. New verification logs are ignored under work/logs. Sections 1–8 and the source-file appendix retain the earlier implementation history; section 9.1 records the final verification separately.

## 1. Implemented

Preserved and completed the existing PHASE 1 foundations from the interrupted attempt. Re-read all 10,968 specification lines in consecutive ranges before changes, reviewed all PHASE 0 documents and existing application/configuration/tests, and checked the immutable source hash. No conflicting architecture or business-rule changes were introduced.

- Next.js App Router, strict TypeScript, Tailwind, shadcn Button, TanStack Query, centralized Kazakh strings and central safe API client. Recharts installed for later actual analytics.
- FastAPI modular monolith with separated route/schema/service/repository/AI/worker/storage/report boundaries. Pydantic settings, SQLAlchemy connection pool, safe errors and structured request logs.
- Actual PostgreSQL/Redis readiness and dependency-independent liveness; OpenAPI export, saved schema, generated TypeScript contracts and drift checks.
- PostgreSQL with pgvector packages, Redis with authentication/AOF, Celery worker and optional empty scheduler, Nginx routing, persistent storage, runtime/development/test Docker stages and two Compose configurations.
- Digest-pinned upstream images and locked application dependencies. Backend is the sole builder of the image shared with worker/beat. Distinct runtime/development tags avoid collisions.
- Random development environment initialization, preserved private .env, safe .env.example, Git/Docker ignore rules and local Git initialization on main. No commit, remote or push was created.
- Executable local and stack verification scripts; browser smoke tests; documentation synchronized with actual foundations and future-phase boundaries.

This phase does not implement catalog/authentication/circulation/AI/analytics/report features. Their package boundaries are explicitly labeled, without mock production APIs or invented results. The complete specification remains the target for subsequent phases.

## 2. Files created

The earlier implementation resumption created docs/openapi.json, frontend/types/api.generated.ts, scripts/verify_phase1.ps1, scripts/verify_stack.py and this report. Git metadata was initialized inside C:\SmartLibrary. Ignored work artifacts include file-hash inventory, dependency/browser caches and verification logs. Final verification created no additional source files.

Earlier PHASE 1 work retained: root environment/ignore/editor/Compose files; backend project/lock/Docker files and app packages/tests; frontend project/lock/Docker/App Router/design/client/test files; infra/nginx/default.conf; environment/schema helper scripts; ML directory documentation; tests/e2e/foundation.spec.ts. The exact source-file inventory is appended below.

## 3. Files modified

Functional/configuration changes in the earlier implementation resumption:

- docker-compose.yml and docker-compose.dev.yml: shared-image build race fixed, separate runtime/dev tags, pinned infrastructure images.
- backend/Dockerfile and frontend/Dockerfile: pin verified upstream digests; remove slow recursive ownership changes over dependencies while retaining non-root processes.
- backend/pyproject.toml: move pytest cache to writable ignored var/pytest-cache, compatible with Windows and container execution.
- frontend/package.json and package-lock.json: explicit ESM package configuration and synchronized lockfile.
- frontend/postcss.config.mjs: named configuration export to resolve lint warning.
- frontend/playwright.config.ts: explicit optional installed-browser channel selection.
- scripts/export_openapi.py: schema drift checking; scripts/init_env.py: configured formatting/import order only.
- tests/e2e/foundation.spec.ts: add backend readiness/Swagger routing checks; preserve original checks.
- README and PHASE 0 architecture/API/AI/database/deployment/security/UI/testing/coverage/phase-plan documents: current behavior, commands, historical blocker clarification and phase boundaries.

Prettier reformatted existing frontend files after the real formatting check failed. This did not replace features or remove assertions. Next.js regenerated next-env.d.ts. The exact changed-file appendix distinguishes these from new files.

MASTER_SPECIFICATION.md and docs/BUSINESS_RULES.md were not modified.

## 4. Database migrations

None. PostgreSQL connectivity and installed extension-package availability were checked. No extension, application schema, table, seed, model or migration was created. Alembic configuration/core schema remain PHASE 2.

## 5. API endpoints and configuration

Existing PHASE 1 endpoints retained: GET /health, /ready, /api/v1/health and /api/v1/ready. Development Swagger/OpenAPI remain at /docs and /openapi.json. Production disables them. Readiness checks SELECT 1 and Redis PING and returns safe HTTP 503 when either dependency is unavailable. Through Nginx, /health belongs to frontend; /api/v1/health identifies backend.

Configuration includes APP_ENV, LOG_LEVEL, FRONTEND_URL, CORS_ORIGINS, ALLOWED_HOSTS, LIBRARY_TIMEZONE, PostgreSQL/Redis fields and optional DSN overrides, future auth/QR credentials/lifetimes, storage/model paths and optional LLM/model selection fields. Details are in DEPLOYMENT.md and .env.example. No real secrets were hardcoded, printed, committed or copied into frontend images.

## 6. Frontend pages/components

The existing / Kazakh application shell, /health route, shared Button, query provider, locale, styling and API client remain intact. No later-phase screen was added. Type generation now has a real exported API contract.

## 7. Tests and verification tooling

- 12 backend foundation tests; none removed or weakened.
- Four frontend API-client/Button tests; none removed or weakened.
- Three Playwright foundation checks, including the new Nginx readiness/docs test.
- scripts/verify_phase1.ps1: fail-fast backend/frontend/build/contract checks, optional E2E.
- scripts/verify_stack.py: real service health, networking/ports, non-root users, HTTP routing, served OpenAPI equality, Nginx syntax, Celery broker ping, extension package availability and opt-in dependency outage/recovery.

These do not count as future business/RBAC/concurrency/vector-query/ML acceptance coverage.

## 8. Commands executed

All paths below are relative to C:\SmartLibrary unless stated otherwise. Docker and affected filesystem/browser operations used approved escalation after sandbox permission failures.

| Commands | Purpose |
|---|---|
| Get-Content in consecutive source ranges; Get-FileHash -Algorithm SHA256; rg/file enumeration | Complete specification and repository review, preservation |
| backend/.venv/Scripts/python.exe scripts/export_openapi.py | Export actual OpenAPI |
| npm run api:generate (frontend) | Generate TypeScript API types |
| npm run lint; npm run typecheck; npm test; npm run build; npm run format:check | Frontend checks |
| npm install --package-lock-only --ignore-scripts; npx --no-install prettier --write . | Synchronize ESM lockfile and repair formatting |
| .venv/Scripts/ruff.exe check .; ruff.exe format --check .; mypy.exe app; pytest.exe -q (backend) | Backend checks |
| backend/.venv/Scripts/ruff.exe check --config backend/pyproject.toml scripts --fix; ruff format for scripts | Check/format maintenance tools |
| ./scripts/verify_phase1.ps1 -E2E with PLAYWRIGHT_CHANNEL=msedge | Full native check runner, including schema/type drift and browser tests |
| docker compose config --quiet | Base configuration validation |
| docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet | Development merge validation |
| docker compose --profile scheduler config --quiet | Optional scheduler configuration validation |
| docker compose build; docker compose up -d --wait --wait-timeout 180 | Runtime images/startup |
| docker compose -f docker-compose.yml -f docker-compose.dev.yml build; corresponding up -d --wait --wait-timeout 180 | Development images/startup |
| docker build --target test -t smartlibrary-backend:test backend; docker run --rm --network none smartlibrary-backend:test | Isolated Linux backend test image |
| python scripts/verify_stack.py --test-outages | Runtime service/isolation/outage/recovery checks |
| python scripts/verify_stack.py --dev --test-outages | Development service/isolation/outage/recovery checks |
| docker inspect/network inspect, compose exec id -u, nginx -t, worker healthcheck, backend SQL extension availability query (inside verifier) | Actual runtime evidence, no mocked dependencies |
| npx --no-install playwright install chromium | Attempted browser download; timed out |
| npm run test:e2e with PLAYWRIGHT_CHANNEL=msedge | Real installed Edge browser tests |
| git init -b main; git check-ignore .env frontend/node_modules backend/.venv work frontend/.next backend/var; git status --short | Local repository and ignore verification |
| docker stats --no-stream; development compose ps; docker desktop status; docker desktop restart; bounded docker info probe | Diagnose/recover the later Linux-engine outage |

## 9. Actual results

| Check | Result |
|---|---|
| OpenAPI export/type generation and drift checks | Passed |
| Backend Ruff lint/format | Passed: 49 Python files formatted; script checks also passed |
| Backend mypy | Passed: 45 source files |
| Native pytest | 12 passed |
| Linux test image pytest, no network | 12 passed |
| Frontend ESLint, TypeScript, Prettier | Passed after fixes |
| Frontend Vitest | Four passed in two files |
| Native production build | Passed |
| Full native verification script including Edge E2E | Passed; three browser checks passed |
| Base/development/scheduler Compose validation | Passed |
| Runtime application image builds and startup | Final rebuild and startup passed after engine recovery |
| Development image builds and startup | Final build and startup passed after engine recovery |
| Runtime and development six-service integration checks | Final checks passed in both configurations, including both dependency outages and recovery |
| PostgreSQL/Redis publication and data network | No host port bindings; only internal data network |
| Application users | Frontend, backend and worker all non-root |
| Nginx | Only loopback ingress; syntax/routing/Swagger/schema checks passed |
| Celery | Targeted ping through real Redis passed, including after recovery |
| Vector/pg_trgm packages | Available; extension creation/query behavior intentionally not executed |
| Final runtime browser checks | Three passed in installed Edge (2.5 seconds) |
| Final development browser checks | Three passed in installed Edge (2.6 seconds); resolves the interrupted rerun |
| Final Docker diagnostics | Engine responsive; Docker 29.2.1, Linux x86_64, Compose 5.0.2, desktop-linux context; six running healthy services |

Earlier development integration output is saved in ignored work/logs/phase1-development-stack.txt. Browser artifacts are ignored under frontend/test-results. Tool outputs record the earlier native/build results. The native lint, formatting, type checks, unit tests, contract generation/drift checks, production build and isolated Linux backend tests were already successful and were not unnecessarily repeated during final verification. Application and test sources remained unchanged. No tests or builds are claimed successful merely from configuration.

### 9.1 Final verification after Docker recovery — 2026-09-27

Re-read the relevant structure/layering, configuration, documentation, Docker/networking, health, reliability, logging and phase-order requirements, and reviewed this report, both Dockerfiles/Compose configurations and the existing verification tests. The complete specification had already been read in the implementation resumption. Docker operations and browser execution used approved escalation. Runtime and development verification ran separately; no build ran concurrently with browser tests.

| Command actually executed | Result |
|---|---|
| docker version; docker info --format with non-secret server fields; docker context ls; docker compose version | All passed; responsive Docker Desktop Linux engine and desktop-linux context |
| docker compose config --quiet | Passed |
| docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet | Passed |
| docker compose --profile scheduler config --quiet | Passed; optional scheduler was not started |
| docker compose --parallel 1 build | Passed; backend and frontend runtime images built, including Next.js production compilation |
| docker compose up -d --wait --wait-timeout 180 | Passed; six healthy services |
| python scripts/verify_stack.py --test-outages | Passed; all runtime checks and both dependency outages/recoveries |
| npm run test:e2e in frontend with PLAYWRIGHT_CHANNEL=msedge and PLAYWRIGHT_BROWSERS_PATH=C:\SmartLibrary\work\playwright | Runtime: three passed |
| docker compose --parallel 1 -f docker-compose.yml -f docker-compose.dev.yml build | Passed; backend and frontend development images built using cached layers |
| docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait --wait-timeout 180 | Passed; six healthy services |
| python scripts/verify_stack.py --dev --test-outages | Passed; all development checks and both dependency outages/recoveries |
| Same npm run test:e2e command against development | Three passed |
| docker compose -f docker-compose.yml -f docker-compose.dev.yml ps; final docker info --format | Six running healthy services; engine remained responsive |

Both stack runs verified actual backend/frontend HTTP 200 liveness, HTTP 200 readiness with PostgreSQL/Redis healthy, Kazakh frontend HTML, Nginx headers/routing/syntax, Swagger, served OpenAPI equality, targeted Celery ping, non-root application processes and available vector/pg_trgm packages. Stopping PostgreSQL and then Redis separately produced readiness HTTP 503 naming only the unavailable dependency while liveness and the UI remained HTTP 200. Each recovery restored readiness HTTP 200 and all six healthy states. No extensions or schema were created.

Container inspection confirmed no host port bindings for PostgreSQL or Redis and that each connects only to the internal data network. Backend, frontend and worker also have no published host ports. Nginx alone publishes 127.0.0.1:8080 to container port 80. EXPOSE entries for 5432/tcp and 6379/tcp are container metadata, not host port publications.

Final running configuration: docker-compose.yml plus docker-compose.dev.yml. Frontend uses smartlibrary-frontend:dev; backend and worker use smartlibrary-backend:dev. Frontend, backend, postgres, redis, worker and nginx are all healthy. The application is reachable at http://localhost:8080 and API docs at http://localhost:8080/docs. Runtime images remain built. Named volumes were preserved.

Saved final evidence under work/logs:

- phase1-final-runtime-build.txt, phase1-final-runtime-startup.txt, phase1-final-runtime-stack.txt, phase1-final-runtime-e2e.txt
- phase1-final-development-build.txt, phase1-final-development-startup.txt, phase1-final-development-stack.txt, phase1-final-development-e2e.txt
- phase1-final-services.txt

No new project defect was found in final verification. No implementation or test assertions required changing. The earlier HTTP 500/timeouts were an environment failure; their specific cause was not established. Recovery is now confirmed by successful builds, live integration checks, browser tests and final engine inspection.

## 10. Problems and fixes

1. Sandbox writes in existing subdirectories and Docker configuration/pipe access failed. Approved escalation enabled the authorized operations without changing ACLs or global Docker configuration.
2. Compose initially built backend and worker into the same image tag concurrently; BuildKit failed with image already exists. Backend now builds once and worker/beat reuse it. Rebuild/startup passed.
3. Frontend formatting failed on 31 files; applied the existing Prettier configuration. Fixed PostCSS export warning and ESM configuration warning. All native checks then passed.
4. Existing local pytest cache was unwritable. The configured cache now uses ignored var/pytest-cache and native/Linux tests passed without that cache warning.
5. Offline npm lockfile refresh lacked an optional platform package. Retried with registry access; succeeded with zero vulnerabilities reported by npm.
6. Chromium download exhausted timeout retries. Used Playwright's explicit msedge channel with installed Edge; three runtime checks passed without removing assertions.
7. Development recursive chown over dependencies was excessively slow. Interrupted that build and used COPY ownership plus small writable directories. The rebuilt development stack passed.
8. During an earlier final runtime rebuild, Docker engine calls stalled and then returned HTTP 500. Concurrent development E2E timed out. Stopped the build and ran an approved Docker Desktop restart, which did not complete while observed. A subsequent 30-second docker info probe timed out. These were recorded as environment failures, not passing checks or proven project defects. After the user reported recovery, this session independently verified the engine and completed every outstanding runtime/development check listed in section 9.1. No system configuration change or project fix was needed during final verification.
9. A bounded diagnostic initially failed due to PowerShell quoting, then ran correctly and recorded the timeout. A multi-file documentation patch was rejected before applying because it targeted the same file twice; split writes succeeded. No source requirements or test assertions were removed to mask these failures.

Non-failing warnings retained visibly: Starlette deprecates the installed httpx TestClient transport; npm marks ESLint 9 as unsupported; Playwright reports conflicting terminal color environment variables. No warnings were hidden through test suppression. Current locked versions passed the listed checks; future dependency upgrades must be validated.

## 11. External requirements and PHASE 2 readiness

There is no remaining PHASE 1 blocker. Docker Desktop's Linux engine is responsive and the approved escalation path works in this Codex environment. Installed Edge provides the verified Playwright browser; the earlier Chromium download timeout does not leave a PHASE 1 browser check unverified. No LLM key, model download or production domain/certificate is required for PHASE 1.

PHASE 2 prerequisites now available: the verified modular project, locked dependencies, typed configuration, private PostgreSQL/Redis services, PostgreSQL vector/pg_trgm packages, SQLAlchemy connection foundation, Alembic dependency, synchronized health API contract, worker/proxy services and passing PHASE 1 test baseline. Keep Docker Desktop running and retain the private local .env and persistent volumes. No further environment recovery action is currently required.

**PHASE 1 COMPLETE — READY FOR PHASE 2.** The remaining gate is explicit user instruction to begin PHASE 2. Before that work, re-read its relevant specification requirements and earlier dependencies and inspect the completed PHASE 1 implementation.

PHASE 2 must begin only after explicit user instruction and a successful PHASE 1 gate. It will add Alembic configuration, vector/pg_trgm extension migrations, UUID/timezone-aware core models, constraints/indexes, separate migration/runtime privilege configuration and real PostgreSQL migration verification. Preserve BOOK/BOOK_COPY, FIFO, explicit librarian issue, ownership/RBAC boundaries and future transaction/concurrency requirements. No PHASE 2 work was performed here.

## 12. Master Specification integrity

SHA-256 before changes and final file-integrity check: DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61. Size 134394 bytes, 10968 lines. File remains untouched. Documentation links were checked and resolve. The earlier implementation resumption created five source/report files and changed 55 existing source/documentation files, excluding ignored artifacts and Git metadata. Final verification updated only the six documentation files listed at the start of this report and created ignored verification logs.

## Appendix: exact file inventory

Paths are relative to C:\SmartLibrary. Ignored secrets, caches, build output and .git metadata are excluded.

### New source/report files in the earlier implementation resumption

- docs/PHASE_1_REPORT.md
- docs/openapi.json
- frontend/types/api.generated.ts
- scripts/verify_phase1.ps1
- scripts/verify_stack.py

### Existing files changed in the earlier implementation resumption

- README.md
- backend/Dockerfile
- backend/pyproject.toml
- docker-compose.dev.yml
- docker-compose.yml
- docs/AI_ARCHITECTURE.md
- docs/API_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATABASE.md
- docs/DEPLOYMENT.md
- docs/IMPLEMENTATION_PLAN.md
- docs/PHASE_0_REPORT.md
- docs/SECURITY.md
- docs/SPECIFICATION_COVERAGE.md
- docs/TESTING.md
- docs/UI_SITEMAP.md
- frontend/Dockerfile
- frontend/app/(public)/page.tsx
- frontend/app/(reader)/README.md
- frontend/app/admin/README.md
- frontend/app/globals.css
- frontend/app/health/route.ts
- frontend/app/layout.tsx
- frontend/app/librarian/README.md
- frontend/app/providers.tsx
- frontend/components.json
- frontend/components/analytics/README.md
- frontend/components/assistant/README.md
- frontend/components/books/README.md
- frontend/components/borrowings/README.md
- frontend/components/layout/README.md
- frontend/components/reservations/README.md
- frontend/components/ui/button.tsx
- frontend/eslint.config.mjs
- frontend/features/admin/README.md
- frontend/features/auth/README.md
- frontend/features/catalog/README.md
- frontend/features/librarian/README.md
- frontend/features/reader/README.md
- frontend/hooks/README.md
- frontend/lib/utils.ts
- frontend/locales/kk.ts
- frontend/next-env.d.ts
- frontend/package-lock.json
- frontend/package.json
- frontend/playwright.config.ts
- frontend/postcss.config.mjs
- frontend/services/api-client.ts
- frontend/tests/api-client.test.ts
- frontend/tests/button.test.tsx
- frontend/tsconfig.json
- frontend/vitest.config.ts
- scripts/export_openapi.py
- scripts/init_env.py
- tests/e2e/foundation.spec.ts

### All retained PHASE 1 application/configuration source files

- .editorconfig
- .env.example
- .gitattributes
- .gitignore
- backend/.dockerignore
- backend/.python-version
- backend/Dockerfile
- backend/alembic/README.md
- backend/app/__init__.py
- backend/app/ai/__init__.py
- backend/app/ai/assistant/__init__.py
- backend/app/ai/categorization/__init__.py
- backend/app/ai/embeddings/__init__.py
- backend/app/ai/recommendation/__init__.py
- backend/app/api/__init__.py
- backend/app/api/v1/__init__.py
- backend/app/api/v1/routes/__init__.py
- backend/app/api/v1/routes/health.py
- backend/app/core/__init__.py
- backend/app/core/config.py
- backend/app/core/errors.py
- backend/app/core/logging.py
- backend/app/db/__init__.py
- backend/app/db/models/__init__.py
- backend/app/db/session.py
- backend/app/main.py
- backend/app/reports/__init__.py
- backend/app/repositories/__init__.py
- backend/app/schemas/__init__.py
- backend/app/schemas/health.py
- backend/app/services/__init__.py
- backend/app/services/administration/__init__.py
- backend/app/services/analytics/__init__.py
- backend/app/services/assistant/__init__.py
- backend/app/services/audit/__init__.py
- backend/app/services/auth/__init__.py
- backend/app/services/borrowings/__init__.py
- backend/app/services/catalog/__init__.py
- backend/app/services/categorization/__init__.py
- backend/app/services/circulation/__init__.py
- backend/app/services/copies/__init__.py
- backend/app/services/health.py
- backend/app/services/notifications/__init__.py
- backend/app/services/recommendation/__init__.py
- backend/app/services/reporting/__init__.py
- backend/app/services/reservations/__init__.py
- backend/app/services/returns/__init__.py
- backend/app/services/search/__init__.py
- backend/app/services/users/__init__.py
- backend/app/storage/__init__.py
- backend/app/tests/conftest.py
- backend/app/tests/test_foundations.py
- backend/app/workers/__init__.py
- backend/app/workers/celery_app.py
- backend/app/workers/healthcheck.py
- backend/pyproject.toml
- backend/scripts/README.md
- backend/uv.lock
- docker-compose.dev.yml
- docker-compose.yml
- frontend/.dockerignore
- frontend/.npmrc
- frontend/.prettierignore
- frontend/.prettierrc.json
- frontend/Dockerfile
- frontend/app/(public)/page.tsx
- frontend/app/(reader)/README.md
- frontend/app/admin/README.md
- frontend/app/globals.css
- frontend/app/health/route.ts
- frontend/app/layout.tsx
- frontend/app/librarian/README.md
- frontend/app/providers.tsx
- frontend/components.json
- frontend/components/analytics/README.md
- frontend/components/assistant/README.md
- frontend/components/books/README.md
- frontend/components/borrowings/README.md
- frontend/components/layout/README.md
- frontend/components/reservations/README.md
- frontend/components/ui/button.tsx
- frontend/eslint.config.mjs
- frontend/features/admin/README.md
- frontend/features/auth/README.md
- frontend/features/catalog/README.md
- frontend/features/librarian/README.md
- frontend/features/reader/README.md
- frontend/hooks/README.md
- frontend/lib/utils.ts
- frontend/locales/kk.ts
- frontend/next-env.d.ts
- frontend/next.config.ts
- frontend/package-lock.json
- frontend/package.json
- frontend/playwright.config.ts
- frontend/postcss.config.mjs
- frontend/services/api-client.ts
- frontend/tests/api-client.test.ts
- frontend/tests/button.test.tsx
- frontend/tsconfig.json
- frontend/types/api.generated.ts
- frontend/vitest.config.ts
- infra/nginx/default.conf
- ml/data/README.md
- ml/evaluation/README.md
- ml/models/README.md
- ml/training/README.md
- scripts/export_openapi.py
- scripts/init_env.py
- scripts/verify_phase1.ps1
- scripts/verify_stack.py
- tests/e2e/foundation.spec.ts
