# Testing and reproducible verification

The final gate executes native, real PostgreSQL/Redis, component, browser, ML,
report and deployment checks. Historical counts remain in PHASE_N_REPORT.md.
TEST_MATRIX.md maps requirements; FINAL_ACCEPTANCE_MATRIX.md maps A–X to evidence.
No skipped database case counts as a PostgreSQL pass.

## Native tools and backend

From C:\SmartLibrary, using Python 3.13, uv and Node 24:

~~~powershell
uv sync --project backend --locked --group dev
npm --prefix frontend ci
backend/.venv/Scripts/ruff.exe check --no-cache --config backend/pyproject.toml backend/app backend/alembic scripts
backend/.venv/Scripts/ruff.exe format --check --no-cache --config backend/pyproject.toml backend/app backend/alembic scripts
backend/.venv/Scripts/python.exe scripts/export_openapi.py --check
backend/.venv/Scripts/python.exe scripts/export_schema_reference.py --check
cd backend
.venv/Scripts/mypy.exe --cache-dir var/mypy-cache
.venv/Scripts/pytest.exe -q --ignore=app/tests/database
cd ..
npm --prefix frontend run api:generate
~~~

The native-only command explicitly excludes database tests: **98 cases**.
The complete final Docker suite executed **358 tests with zero skips**,
including these 98 and 260 database/Redis-backed cases. The subsequently added
exact two-turn assistant acceptance case passed separately: all **359 current cases**
executed, comprising 98 native and 261 database-backed cases, without skips.

## Real PostgreSQL/Redis

Download pinned local models and train categorization first (commands below).
Start dependencies and build the test target, then run:

~~~powershell
docker compose up -d --wait postgres redis
docker compose build database-tests
docker compose run --rm -v C:/SmartLibrary/work/model-cache:/models:ro -e MODEL_CACHE_DIRECTORY=/models -e HF_HUB_OFFLINE=1 database-tests
~~~

The test service mounts the versioned ML dataset read-only. It creates its own
random databases, provisions restricted roles, applies all migrations, verifies
head/drift, downgrades to base, re-upgrades, seeds and runs pytest. Only its own
databases and Redis namespaces are removed. Development data is never reset.
Transactions, constraints, barriers, locks, vectors and Redis are real. An actual
Celery subprocess receives a Redis task and is restarted to verify deduplication.
SQLite is not used as a PostgreSQL substitute.

For a targeted file, add -e PYTEST_ADDOPTS=app/tests/database/domain/test_scheduled.py
before database-tests. With pytest 9, group multiple explicit paths by directory;
interleaving parent/domain paths disrupts fixture lookup. During edits, source
may be mounted at /app/app and migrations at /app/alembic instead of rebuilding
unchanged dependencies. Final image builds remain required.

## Frontend

~~~powershell
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
~~~

The complete component suite has **70 tests**. HTTP-boundary component stubs test
UI states; real database/browser suites verify business behavior. Generated
TypeScript comes from docs/openapi.json, never hand-edited contracts.

## Isolated browser stack

Initialize once; the helper refuses to overwrite an existing private environment:

~~~powershell
python scripts/init_e2e_env.py
$e2e = @('-p','smartlibrary-e2e','--env-file','work/e2e.env','-f','docker-compose.yml','-f','docker-compose.dev.yml','-f','docker-compose.e2e.yml')
docker compose @e2e build backend frontend
docker compose @e2e up -d --wait postgres redis
docker compose @e2e run --rm database python -m app.db.manage upgrade
docker compose @e2e run --rm database python -m app.db.manage seed
docker compose @e2e up -d --wait --wait-timeout 180
backend/.venv/Scripts/python.exe scripts/run_e2e.py --label final
docker compose @e2e stop
~~~

Separate database/Redis/uploads use port 8081. The initialized smartlibrary_models
volume is shared read-only; prepare model artifacts in the primary stack first.
On Windows the runner uses installed Edge. Set PLAYWRIGHT_CHANNEL=chromium after
installing the matching Playwright browser on other hosts. Credential-bearing
traces, videos and screenshots are disabled.

The runner initializes only smartlibrary:e2e:* counters before each file, refuses
a non-test app/namespace and preserves actual policy limits. No counter is reset
inside a case. Domain APIs, auth and registration remain real. Rate-limit rejection
has separate real Redis coverage. Do not clear development/production counters.

Use a basename such as pickup.spec.ts for targeted runs. Browser expectations
allow 15 seconds for cold development-route compilation. pages.spec.ts traverses
56 public/role page visits with real API responses, loading/error and JS checks;
application alerts are scoped to main, excluding Next.js's route announcer.
Workflow cases separately prove verification makes no borrowing until explicit
issue, Reader history after return and FIFO advancement. See TEST_MATRIX.md.

## ML and reports

SEMANTIC_SEARCH.md and CATEGORIZATION.md give pinned download, benchmark, training
and generation commands. Repeat benchmark_search.py without --download to use
cached models. Train twice with different --output directories and compare
coefficients, revision, thresholds and metrics excluding generated_at.
Synthetic vectors are not model-quality evidence.

The external LLM is the only scripted boundary in assistant integration tests;
tools, data, ownership and orchestration are real. Without credentials, the actual
browser verifies safe unavailability and persisted failure history. Live provider
answer quality remains an explicit external requirement.

Report tests generate/reopen all four PDF/XLSX pairs from persisted rows, checking
date ranges/summary metrics, typed cells, authorization and no auth fields.
Final verification also renders every PDF page and visually checks Kazakh/Cyrillic,
pagination and tables. Files/renders stay in ignored work/.

## Infrastructure and recovery

~~~powershell
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose build backend frontend
docker compose up -d --wait --wait-timeout 180
python scripts/verify_stack.py --test-outages
docker compose -f docker-compose.yml -f docker-compose.dev.yml build backend frontend
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --wait --wait-timeout 180
python scripts/verify_stack.py --dev
docker compose run --rm database python -m app.db.manage check
docker compose run --rm -e PYTHONPATH=/app -v C:/SmartLibrary/scripts:/verification:ro database python /verification/verify_database.py
~~~

Outage checks briefly stop/restore local PostgreSQL/Redis in finally blocks;
never run against shared production. The read-only inspector compares actual
schema, roles, timestamps, vectors and relationships. PRODUCTION_DEPLOYMENT.md
documents the independent TLS setup/checks. run_tls_browser.py uses pinned Linux
Chromium when Windows antivirus intercepts the local test CA; verify_production.py
independently verifies its chain/hostname. No OS security settings are changed.
BACKUP_RECOVERY.md documents pg_dump, image/artifact archives, checksums and restore
into a new disposable database. Volumes are not backups.

## Evidence policy

Save logs in work/logs without credentials or resolved Compose environments.
Distinguish executed checks, inherited evidence and external limitations.
Do not delete, skip, xfail or weaken valid tests. Use targeted checks during edits
and the complete final gate at PHASE 22.
