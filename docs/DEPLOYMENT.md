# Development deployment

Runtime/development instructions are below. Production HTTPS setup is documented
in PRODUCTION_DEPLOYMENT.md; actual recovery steps are in BACKUP_RECOVERY.md.
The original foundations remain intact. Sources: PARTS 127, 178–182, 193–195, 197
and acceptance V/W/X. Phase reports distinguish newly executed verification.

## Start and stop

PHASE 10 adds @zxing/browser to the frontend dependency lock. Rebuild frontend
when upgrading from an earlier image; `docker compose -f docker-compose.yml -f
docker-compose.dev.yml build frontend` then `up -d --no-deps --wait frontend`
with the same Compose files. No database reset is needed. Camera requires HTTPS
or localhost plus browser/device permission; manual-number fallback remains available.

From C:\SmartLibrary, with Docker Desktop's Linux engine available:

```powershell
python scripts/init_env.py
docker compose config --quiet
docker compose build backend
docker compose up -d postgres redis --wait
docker compose run --rm database python -m app.db.manage upgrade
docker compose run --rm database python -m app.db.manage check
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

The helper exclusively creates .env from .env.example with independent random local credentials. It refuses to overwrite an existing .env. For an existing PHASE 1 environment use `python scripts/init_database_env.py` instead; it preserves nonempty values and adds missing role/seed credentials. Do not print .env, resolved Compose environments or unrestricted container inspection into shared logs.

For source mounts and reload:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis --wait
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm database python -m app.db.manage upgrade
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm database python -m app.db.manage check
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build --wait --wait-timeout 180
```

Use the same file arguments for later development commands. Switching to base Compose recreates application containers using runtime images; named volumes persist. `docker compose down` removes containers/networks but retains volumes. `down -v` deletes data and is not a routine restart command.

Default endpoints: localhost:8080 for frontend; /docs and /openapi.json for development API docs; /api/v1/health for backend liveness; /api/v1/ready for dependency readiness; /health for frontend liveness; /nginx-health for Nginx itself.

Authentication pages are /login and /register; auth APIs use /api/v1/auth.
Seeded accounts use private DEV_SEED_PASSWORD. Browser traffic must use the
configured same-origin Nginx URL so Origin/CSRF/cookie checks agree. Changing
HTTP_PORT requires updating FRONTEND_URL/CORS_ORIGINS together. The operator
and database-test services receive JWT_SECRET for settings validation; the
frontend never receives it.

## Services and images

| Service | Image/target and purpose |
|---|---|
| backend | Python 3.13.7 + uv 0.12.19; runtime/development/test stages; sole builder of shared Python image |
| worker | Reuses backend image; JSON-only Celery, default queue, concurrency 2, targeted control ping |
| frontend | Node 24.14.0; Next.js standalone runtime or source-mounted development server |
| postgres | pgvector 0.8.2 / PostgreSQL 17 image; persistent database storage |
| redis | Redis 7.4 Alpine; password, AOF and persistent storage |
| nginx | Nginx 1.28 Alpine; local HTTP ingress and frontend/API routing |
| ml-worker | Backend image; dedicated ml queue, one inference process, persistent model cache, targeted ping |
| beat | Backend image; missing-vector sweep every 60 seconds, scheduler heartbeat health; circulation expiration/reconciliation/reminders every 60 seconds |
| database | Opt-in operator profile; explicit role/extension/migration/check/seed commands, internal data network only |
| database-tests | Opt-in testing profile; backend test target and isolated real PostgreSQL integration suite |

Upstream image digests are pinned in Dockerfiles/Compose; uv.lock and package-lock.json fix dependencies. Update tags/digests/locks deliberately and rerun verification. Runtime images use :local and development images use :dev. Worker/beat do not build competing copies of the same tag. Build backend before starting worker alone on a fresh system. Windows dependencies are never mounted over Linux node_modules/virtual environments.

API, worker and frontend run as non-root with no-new-privileges. COPY ownership and writable application/cache directories avoid recursive ownership changes over installed dependency trees.

## Networking and health

Only Nginx publishes `127.0.0.1:${HTTP_PORT}:80`. PostgreSQL/Redis have no host ports and attach only to the internal data network. API/worker connect to data and application networks; Nginx/frontend only to application. EXPOSE metadata is not a host publication.

PostgreSQL uses pg_isready, Redis authenticated PING, backend readiness actual SELECT 1 and Redis PING with timeouts. Liveness does not connect to dependencies. Worker health expects a reply from its exact container hostname through Redis. Frontend/Nginx use HTTP checks. Startup waits for dependency health; pool pre-ping and Celery connection retry support recovery.

`python scripts/verify_stack.py --test-outages` checks eight services, networking, non-root users, routing/contracts, extension availability and Celery ping, then stops/restores PostgreSQL and Redis individually. It checks readiness 503 while UI/liveness stay 200 and readiness 200 after recovery. Dependencies are restored in finally blocks. Add --dev for the development override. Use outage tests only on this local development stack.

## Environment variables

| Variables | Behavior |
|---|---|
| APP_ENV, LOG_LEVEL | development/test/production; production rejects DEBUG |
| HTTP_PORT | Loopback ingress; change FRONTEND_URL/CORS_ORIGINS together |
| FRONTEND_URL, CORS_ORIGINS, ALLOWED_HOSTS | Explicit origin and JSON lists, no wildcard origins/hosts |
| LIBRARY_TIMEZONE | Valid IANA zone; example Asia/Qyzylorda; worker timestamps use UTC |
| POSTGRES_HOST/PORT/DB/USER/PASSWORD | PostgreSQL bootstrap owner for service/operator; API/worker receive the application role through explicit mapping |
| APP_DB_USER/PASSWORD | Restricted application role; required before starting the new API/worker environment |
| MIGRATION_DB_USER/PASSWORD | Non-superuser DDL owner; operator/test services only |
| DEV_SEED_PASSWORD | Private development fixture password; seed refuses production |
| DATABASE_URL | Optional runtime postgresql+psycopg DSN using the restricted role; percent-encode credentials |
| REDIS_HOST/PORT/PASSWORD, REDIS_URL | Redis fields or optional redis/rediss override |
| JWT_SECRET, QR_ENCRYPTION_KEY | JWT signing/HMAC and separate QR encryption secret; JWT_SECRET requires 32+ non-default characters in every environment; production requires independent secrets |
| ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL | Access-token seconds and absolute refresh-family seconds; default 900 / 2592000 |
| TRUST_PROXY_HEADERS | False for direct backend use; Compose sets true behind Nginx, which overwrites client-address headers; do not expose backend directly with this enabled |
| AUTH_LOGIN_IP_LIMIT, AUTH_LOGIN_ACCOUNT_LIMIT, AUTH_LOGIN_WINDOW_SECONDS | Redis login limits: default 30/IP, 10/account in 900 seconds |
| AUTH_REGISTER_LIMIT | Default 10 registrations/IP/hour |
| AUTH_REFRESH_LIMIT | Default 120 refreshes/IP/minute |
| UPLOAD_DIRECTORY, MODEL_CACHE_DIRECTORY | Persistent /app/var/uploads and /app/var/models foundations |
| LLM_PROVIDER, LLM_MODEL, GROQ_API_KEY, LLM_API_KEY | Optional assistant provider/model and private credential. Groq uses GROQ_API_KEY and OpenAI uses LLM_API_KEY. |
| EMBEDDING_MODEL, EMBEDDING_MODEL_REVISION | Pinned E5 base selected by PHASE 12 evaluation; see SEMANTIC_SEARCH.md for download/generation and immutable revision |

Pydantic validates configuration at process creation. Database/cache passwords require 16+ non-default characters; operator-provisioned role passwords require at least 32. The initializer generates stronger random values. Business defaults are now migration data in `system_settings`; business services read them for each operation. Secrets are not supplied to frontend containers or browser bundles.

Additional auth safety limits are fixed in the rate-limit module: 240 CSRF
requests/IP/minute, 120 session mutations/IP/minute and 10 password changes/IP
per 900 seconds. Tests override the typed auth_rate_namespace setting to isolate
their Redis keys. AUTHENTICATION.md records failure and Retry-After behavior.

## Windows execution environment

The Docker development frontend uses `next dev --webpack`. PHASE 4 observed
Turbopack dev omitting `/books/[id]/copies` from route discovery despite readable
files, including after container recreation. The identical route returned 200
with webpack. Native production builds retain the existing build command.
Confirm the container sees current source before diagnosing a route as an API defect.
Development Compose explicitly enables WATCHPACK_POLLING=1000 and
WATCHFILES_FORCE_POLLING=true because Windows Docker bind mounts did not reliably
notify the development frontend of edits. These settings apply only to
development; production image behavior is unchanged.
PHASE 4 cover files use the existing persistent uploads volume. Operational
orphan cleanup and image validation limits are documented in CATALOG.md.

Current verified Docker CLI/server: 29.8.0, Compose 5.5.1, Docker Desktop 4.92.0, Linux x86_64 on WSL2. PHASE 1 used Docker 29.2.1 and Compose 5.0.2. Default Codex sandbox Docker calls fail on configuration/pipe access; approved escalation works. Existing subdirectory writes may also require approved escalation. No global Docker configuration, pipe ACL or firewall changes were made by the implementation. This supersedes PHASE 0's engine-unavailable observation.

Historical engine/disk failures and their recovered checks remain in PHASE_1_REPORT.md
and PHASE_2_REPORT.md. Current deployment has eight services, including the dedicated
ML worker and Beat. No project volume was pruned or reset during recovery.

## Database and production boundaries

Five migrations install vector/pg_trgm, 27 domain/support tables, 16 enums,
constraints/indexes, seven settings and database guards. Operator tooling provisions
separate runtime/migration privileges. Apply the schema before the new runtime
role is used. See DATABASE.md for migrations, optional development seed and
isolated database tests. Application startup never runs create_all or migrations.

Local HTTP is loopback-only. docker-compose.production.yml adds certificate-backed
HTTPS, canonical redirects, HSTS, safe logs and restricted origin configuration.
Auth cookies are Secure with production prefixes; development HTTP intentionally
omits Secure. Both modes overwrite ingress client-address headers. See
PRODUCTION_DEPLOYMENT.md for setup, first Admin and the local verification boundary.

scripts/backup.py exports actual pg_dump, uploads and learned artifacts with a
manifest. scripts/verify_backup.py restores only into its new disposable database
and verifies live schema/data access. See BACKUP_RECOVERY.md for the executed
rehearsal, required secret storage and off-site copy responsibilities.

## Categorization artifact

Run the offline training command in CATEGORIZATION.md and install its model.json
under MODEL_CACHE_DIRECTORY/categorization/. Docker uses the shared model volume
at /app/var/models/categorization/model.json. Include this artifact and its
versioned dataset/configuration in backups. Missing artifacts fail safely without
affecting catalog/circulation. PHASE 14 used native training and verified Docker inference.

## Assistant provider

Configure the provider in the private Compose environment file and recreate the
backend with the same Compose files and project name used to start it.
The [assistant setup guide](AI_ASSISTANT.md#configuration-and-unavailable-behavior)
lists Groq and OpenAI settings and a reader-facing availability check.

## Report dependencies

PHASE 17 locks ReportLab/openpyxl and bundles licensed Noto Sans in backend/app/assets.
Rebuild backend-derived images after pulling these changes. Report generation needs
no external font/network/storage service; files are returned privately in memory.


PHASE 19 introduces frontend/proxy.ts and per-response script nonces. HTML now
uses request-time rendering/no-store; static assets remain cacheable. Development
mounts the proxy; runtime images include it on rebuild. Production eval is disabled.
