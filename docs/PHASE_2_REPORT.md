# PHASE 2 implementation report

PHASE 3 addendum: authentication/session/RBAC work was subsequently authorized
and completed on this schema, with no new migration. The full expanded backend
suite passed 126 cases against PostgreSQL/Redis with zero skips. See
PHASE_3_REPORT.md. The original PHASE 2 scope and readiness below are historical.

Date: 2026-09-27. Scope: PostgreSQL, pgvector, Alembic and the complete core
database schema only. **PHASE 2 COMPLETE — READY FOR PHASE 3.**
PHASE 3 has not started and requires explicit user instruction.

After the user expanded C: and recovered Docker Desktop, all three migrations
were applied to the real development database. Live schema, seed and role
inspection passed. A fresh PostgreSQL database passed upgrade/downgrade/upgrade
and all **54 tests with zero skips** (41 database cases and 13 other cases).
Runtime/development startup and three browser regression checks also passed.
Section 8 preserves the initial blocked attempt; section 10 records the final
executed verification. The storage blocker is resolved.

## 1. Inspection and preserved foundations

- Read all 10,968 lines of the Master Specification in consecutive ranges,
  including PARTS 1–200, final acceptance scenarios, working rules, reviews,
  deliverables, non-negotiable requirements and final instruction.
- Reviewed PHASE 0/1 reports, architecture, database/business/security/AI/test
  plans, current Docker/environment setup, backend foundations and frontend
  package/contracts. No workspace or parent AGENTS.md was found.
- Preserved Next.js/TypeScript/Tailwind/shadcn, FastAPI modular monolith,
  SQLAlchemy/Pydantic/Alembic, PostgreSQL/pgvector, Redis/Celery, Nginx and existing
  frontend/backend boundaries. No later-phase endpoint or business service was
  implemented. Existing health behavior and API contracts were preserved.
- Git is initialized on `main`; project files are still untracked. There is no
  committed baseline to present as a clean diff. No commit, push or remote was
  created. The file manifest below identifies this phase's changes.
- At resumption, re-read the relevant schema, business-rule, security, search,
  analytics, AI, notification, concurrency, migration/seed and testing clauses;
  reviewed this report and all three existing revisions. A 154-file SHA-256
  baseline was saved before edits. Existing models, revisions, seeds, operator
  role logic, original tests, frontend and Compose files were preserved.

## 2. Implemented

- 27 SQLAlchemy tables, 16 PostgreSQL enum types, UUID keys and timezone-aware
  timestamps. BOOK and physical BOOK_COPY remain separate. Relationships and
  explicit foreign keys support catalog, circulation, notifications, analytics,
  AI history/model provenance, settings, audit and refresh-session storage.
- Frozen Alembic revisions install extensions and schema, followed by six
  persistent configurable defaults and database guards. No `create_all`, startup
  migration, SQLite substitution or production mock API was introduced.
- Unique/check constraints and partial indexes defend same-kind circulation
  exclusivity, QR state fields, reference ownership, data types, event deduplication
  and review/analytics integrity. Service-level transaction workflows remain in
  their prescribed phases.
- Explicit operator CLI provisions distinct owner/migrator/application roles,
  applies reviewed migrations and restricted runtime grants, checks drift, seeds
  development data and manages an isolated PostgreSQL test database.
- Versioned vector spaces retain model/revision/dimension/configuration/source
  provenance. Stored vectors must match their model's dimension. Model selection
  still requires the PHASE 12 multilingual benchmark; no fake AI data was seeded.
- Development/test-only, transactional, repeat-safe seed infrastructure with
  real Argon2id hashes and random hashed/encrypted READY QR material. It creates
  6 accounts, 10 categories, 12 titles, 24 copies and circulation/engagement
  fixtures. Unknown ISBN/page counts remain absent. No login service exists yet.
- The original 36 PostgreSQL cases cover real constraints, extensions,
  privileges, seeds, rollback and competing connections. Five new live cases
  verify Alembic comparison behavior. All 41 executed successfully; a separate
  native case proves that the seed refuses production.
- Explicit Compose runtime environment mapping prevents API/worker inheritance
  of owner/migration/seed credentials. Opt-in operator/test services use the
  internal data network. PostgreSQL/Redis still have no published ports in either
  validated Compose configuration. Actual runtime/development container bindings
  were also inspected successfully.

## 3. Migrations

| Revision | Parent | Contents | Live application |
|---|---|---|---|
| `0001_extensions` | base | `vector`, `pg_trgm`; operator privileges required | Applied and tested |
| `0002_core_schema` | `0001_extensions` | 27 tables, 16 enums, one reservation-number sequence, all core constraints/indexes | Applied and tested |
| `0003_defaults_and_guards` | `0002_core_schema` | Six system settings, seven update-time triggers, audit UPDATE/DELETE/TRUNCATE guards and immutable embedding provenance | Applied and tested |

All three original revision files remain unchanged. Development is at
`0003_defaults_and_guards (head)` with no new upgrade operations detected.
The isolated PostgreSQL runner applied all three from a fresh database, checked
drift, downgraded the empty test schema to base, upgraded again and rechecked
head/drift. All steps passed. The earlier offline SQL render remains a separate
static check in ignored `work/logs/phase2-schema.sql`; live evidence is recorded
in `work/logs/phase2-final-postgresql-tests.txt` and `phase2-final-head.txt`.

Downgrading the initial schema destroys domain data; it is intended for an empty
disposable test database. Operational rollback needs a reviewed backup/restore
plan. Extension downgrade leaves extensions installed to preserve dependencies.

Initial settings are `borrow_period_days=14`, `max_books_per_user=5`,
`reservation_hold_hours=48`, `return_reminder_days=2`,
`block_borrowing_if_overdue=true` and `block_reservation_if_overdue=true`.
Numeric bounds and JSONB type checks are stored alongside the values. These
values are migration seed data, not hardcoded business-service results.

## 4. Tables, constraints and indexes

The counts below were checked in metadata and independently verified against
the **actual development PostgreSQL catalog**. Every table has one UUID primary
key. In total: **27 primary keys, 48 foreign-key
constraints, 31 unique constraints, 60 check constraints and 76 additional
indexes**. Four additional indexes are partial unique indexes. Primary/unique
constraint indexes are implicit and excluded from the 76 count. The live total
is **134 indexes**, including those 58 constraint indexes. All constraints were
validated; 16 enum definitions, timezone-aware timestamps, composite references,
vector type/dimension guards and 10 database triggers were inspected.

| Table | Foreign keys | Unique constraints | Checks | Additional indexes |
|---|---:|---:|---:|---:|
| users | 0 | 1 | 3 | 3 |
| refresh_sessions | 2 | 3 | 5 | 2 |
| books | 1 | 1 | 5 | 7 |
| book_copies | 1 | 2 | 3 | 2 |
| authors | 0 | 0 | 1 | 1 |
| book_authors | 2 | 1 | 0 | 1 |
| categories | 0 | 1 | 1 | 1 |
| book_categories | 2 | 1 | 0 | 1 |
| publishers | 0 | 0 | 1 | 1 |
| reservations | 3 | 4 | 7 | 8 |
| borrowings | 5 | 2 | 2 | 9 |
| favorites | 2 | 1 | 0 | 1 |
| user_interactions | 4 | 1 | 1 | 7 |
| search_events | 1 | 0 | 3 | 4 |
| notifications | 4 | 1 | 2 | 4 |
| user_category_preferences | 2 | 1 | 1 | 1 |
| embedding_models | 0 | 2 | 3 | 0 |
| book_embeddings | 2 | 1 | 3 | 1 |
| ai_conversations | 1 | 0 | 0 | 1 |
| ai_messages | 1 | 0 | 5 | 2 |
| ai_message_books | 2 | 2 | 1 | 1 |
| category_prediction_runs | 3 | 1 | 3 | 4 |
| category_predictions | 4 | 1 | 2 | 4 |
| category_prediction_selections | 2 | 1 | 0 | 1 |
| recommendation_impressions | 2 | 2 | 2 | 4 |
| system_settings | 1 | 1 | 3 | 1 |
| audit_logs | 1 | 0 | 3 | 4 |

[SCHEMA_REFERENCE.md](SCHEMA_REFERENCE.md) enumerates all columns, enum values,
foreign-key/delete rules, unique/check definitions and index SQL. It is generated
from the models and drift-checked. [DATABASE.md](DATABASE.md) explains their
business and security purpose.

The separate, read-only live inspection output is saved under ignored
`work/logs/phase2-live-database.json`. PostgreSQL reported **17.10**, extension
**vector 0.8.2** (pgvector) and **pg_trgm 1.6**. Real tests exercised compatible
3/4-dimensional model spaces, cosine distance, invalid dimensions and zero-vector
rejection. This verifies storage behavior; the actual multilingual embedding
model remains subject to PHASE 12 evaluation.

Persisted development rows were independently counted: 6 users, 12 authors,
2 publishers, 10 categories, 12 books, 12 book-author links, 18 book-category
links, 24 copies, 6 reservations, 5 borrowings, 8 favorites, 4 preferences,
16 interactions, 3 search events, 2 notifications, 6 audit logs and 6 settings.
Other domain tables are empty as intended; no fabricated embeddings, predictions,
AI messages or recommendation impressions were inserted. Copy states are
18 AVAILABLE, 2 BORROWED and one each RESERVED/DAMAGED/LOST/MAINTENANCE.
Reservations include 2 WAITING and one each READY/COMPLETED/CANCELLED/EXPIRED;
loans include 1 BORROWED, 1 OVERDUE, 2 RETURNED and 1 LOST.
Actual Argon2id verification, QR decrypt/hash matching, reference consistency,
setting values and restricted runtime privileges all passed.

Notable defenses:

- Unique active user/book reservation; unique READY copy; unique active loan copy;
  unique fulfilled reservation; unique impression click.
- Composite reservation/book/copy, borrowing/reservation/user/copy, notification
  owner/reference, refresh family and recommendation attribution foreign keys.
- FIFO, expiry, due-date, copy allocation, user/history, actor/action/entity/time,
  search/result-count and event/source query indexes, plus five trigram GIN indexes.
- READY-only QR fields, consistent hold/loan dates, damaged/archive copy rules,
  typed setting bounds, nonzero/matching vector dimensions and valid score ranges.
- Historical references use RESTRICT; archive/inactivation preserves history.
  Cascades are limited to deliberate association, preference, derived-vector or
  owned-message lifecycles. Runtime DELETE is granted only on listed tables.

## 5. Architectural decisions and phase boundaries

1. PostgreSQL is the sole schema/concurrency authority. An explicit operator runs
   Alembic; API startup stays free of DDL. Operator, migration and runtime roles
   are separate so normal requests cannot own schema or mutate audit history.
2. UUID entity identity is separate from readable sequence-generated reservation
   numbers. Number gaps are acceptable; FIFO uses reservation time and UUID tie-break.
3. QR hashes and encrypted recoverable material are separate deferred fields.
   Terminal states erase credentials. Storage does not verify a QR or issue a book.
4. Model-specific dimension/provenance constraints permit benchmarking and model
   migration without fixing an unmeasured embedding model. Actual search, model
   loading, re-embedding and measured approximate indexes remain PHASE 12 work.
5. Concrete notification FKs plus a generated related ID avoid dangling generic
   references. AI book references likewise point to actual catalog records.
6. Prediction runs and reviewed category sets retain manual changes and distinguish
   probabilities from similarities/decision scores. Impression attribution supplies
   future CTR inputs without manufacturing live metrics.
7. Constraints backstop service transactions; they do not implement cross-table
   copy-state consistency, FIFO advancement, active-account/staff-role decisions,
   overdue/limit enforcement or authorization. Those requirements remain explicit
   dependencies for PHASES 3–8 and later analytics/AI workflows.

No technical contradiction requiring an architecture or business-rule change
was found. Schema choices and deferred service enforcement are documented rather
than treated as completed later-phase behavior.

## 6. Files created

- `backend/app/db/base.py`, `backend/app/db/enums.py`
- `backend/app/db/models/users.py`, `catalog.py`, `circulation.py`, `engagement.py`,
  `administration.py`, `ai.py`
- `backend/app/db/manage.py`, `seed.py`, `seed_data.py`
- `backend/app/db/migration_comparison.py` (added during live verification)
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_extensions.py`, `0002_core_schema.py`,
  `0003_defaults_and_guards.py`
- `backend/app/tests/database/__init__.py`, `conftest.py`, `test_schema.py`,
  `test_ai_analytics_security.py`, `test_concurrency.py`
- `backend/app/tests/database/test_migrations.py` (five live regression cases)
- `scripts/init_database_env.py`, `scripts/export_schema_reference.py`
- `docs/SCHEMA_REFERENCE.md`, `docs/PHASE_2_REPORT.md`
- Ignored workspace review helpers and evidence under `work/`, including the
  migration-generation helper, resumption source hash baseline, read-only live
  catalog inspector and `work/logs/phase2-*` outputs. Migrations do not
  depend on those temporary helpers at runtime.

## 7. Files modified and configuration

- `backend/app/db/models/__init__.py`: registers all mappings.
- `backend/app/db/session.py`: operator-owned migration lifecycle documentation.
- `backend/pyproject.toml`, `backend/uv.lock`: Argon2id and encryption dependencies,
  stable Ruff import classification and pgvector typing boundary configuration;
  during resumption, minimum Alembic 1.18 for its public plugin API (lock 1.20.0).
- `backend/alembic/env.py`: registers the narrowly scoped comparison plugin;
  ordinary type/default/nullability comparison remains enabled.
- `backend/Dockerfile`: includes Alembic files in development/runtime images.
- `docker-compose.yml`, `docker-compose.dev.yml`: explicit runtime credentials,
  opt-in database/operator/test services and development migration mounts.
- `.env.example`, `scripts/init_env.py`: safe role/seed variables and random
  credential generation. Private ignored `.env` gained missing role/seed values;
  existing nonempty secrets were preserved and no values were printed.
- `README.md`; `docs/DATABASE.md`, `ARCHITECTURE.md`, `SECURITY.md`,
  `AI_ARCHITECTURE.md`, `DEPLOYMENT.md`, `TESTING.md`, `IMPLEMENTATION_PLAN.md`,
  `SPECIFICATION_COVERAGE.md`; backend Alembic/scripts READMEs.
- `docs/PHASE_0_REPORT.md`, `docs/PHASE_1_REPORT.md`: current-status addenda only;
  prior verification evidence remains historical.

No frontend source, API endpoint/response schema, generated frontend contract,
Master Specification, host firewall or Docker ACL/configuration was changed.
No project volume or unrelated user data was deleted. Only regenerable workspace
package/Next.js caches were reclaimed while diagnosing disk exhaustion.

The recovery resumption added only the comparison module and its regression
test file to application/test source. It modified `backend/alembic/env.py`,
`backend/pyproject.toml`, `backend/uv.lock` and the affected documentation listed
above. Hash comparison confirms the existing models, three revisions, seeds,
role/operator logic, original tests, frontend and Compose implementation remained
intact. The earlier entries describe the whole PHASE 2 implementation, not a
recreation during resumption.

## 8. Initial attempt — historical commands and results

Commands below ran from `C:\SmartLibrary`, except those explicitly shown under
`backend`. Docker operations used approved escalation where required. These are
the earlier results before storage recovery; section 10 supersedes the blocker
and incomplete verification status without erasing that history.

| Command/check | Actual result |
|---|---|
| Workspace/specification reads, repository/phase inspection | Passed; complete specification read before implementation |
| `python scripts/init_database_env.py` | Passed; private missing credential fields initialized |
| Python lock/dependency update and native dependency installation | Completed; new hashing/encryption dependencies import in tests |
| `backend/.venv/Scripts/ruff.exe check --config backend/pyproject.toml backend/app backend/alembic scripts` | Passed after fixes |
| Same Ruff scope with `format --check` | Passed; 73 Python files formatted at final check |
| From backend: `.venv/Scripts/mypy.exe --cache-dir var/mypy-cache` | Passed; 56 source files |
| From backend: `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider` | 13 passed, 36 skipped; no database pass claimed |
| `backend/.venv/Scripts/python.exe -B scripts/export_openapi.py --check` | Passed; previous API contract unchanged |
| SQLAlchemy `configure_mappers()` and metadata inventory | Passed; 27 tables, 16 enums and counts in section 4 |
| From backend: `.venv/Scripts/python.exe -m alembic upgrade head --sql` | Passed through all 3 revisions; SQL saved under work/logs |
| `backend/.venv/Scripts/python.exe -B scripts/export_schema_reference.py` and `--check` | Export/check passed; generated reference matches models |
| `docker compose config --quiet` | Passed |
| `docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet` | Passed |
| In-memory inspection of both resolved Compose configurations | Passed: PostgreSQL/Redis publish no ports, use the internal data network, Nginx is loopback-only, and API/worker use distinct runtime credentials without migration/seed fields; no secrets printed |
| Development `docker compose ... build backend` | First attempt failed on BuildKit metadata I/O; retry built successfully after cache reclamation/restart |
| `docker desktop restart` | Command completed during recovery attempt; subsequent storage failures returned |
| Development `docker compose ... run --rm database python -m app.db.manage upgrade` | Failed creating container; Python migration command never started |
| `docker system df` | Failed reading image storage with I/O error |
| Initial attempt's last `docker info --format ...` | Reported "Docker Desktop is unable to start"; not counted as successful despite CLI exit code 0 |
| `Get-PSDrive -Name C` | Disk reached 0 free bytes; later space fluctuated below 1 GB, with 694,390,784 bytes free at the final check and Docker still unavailable |
| `Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256` | Unchanged hash; see section 11 |
| Local Markdown link check | Passed across 18 documentation files |
| `git check-ignore .env backend/.venv work/logs/phase2-schema.sql` | All three private/generated paths are ignored |

The native pytest run disabled cache writes because of disk pressure. Its two
warnings were the resulting unused `cache_dir` configuration warning and the
existing Starlette/httpx deprecation warning. No valid assertion was removed or
weakened to produce a pass. The 36 PostgreSQL tests skip explicitly without the
runner's isolated database environment.

The successful development-image checkpoint is
`smartlibrary-backend:dev`, manifest
`sha256:d55aaa5fad928212ea99e386897fcc2d41b1f2c810a75f68aec6ae67e33ac425`.
Subsequent static-review fixes were made, so this was not a final-source image
verification. At that time, the final image rebuild, runtime target, test target, schema
application, seeds, grants, live catalog inspection, Alembic drift check,
upgrade/downgrade/upgrade, PostgreSQL tests, stack readiness and browser regression
were pending. Section 10 now records their successful execution. Unchanged
frontend lint/type/unit/build evidence remains in the
PHASE 1 report; it was not rerun or presented as a PHASE 2 execution.

## 9. Problems found and corrected

- Frozen migration generation needed explicit native-enum ownership and fully
  qualified SQLAlchemy text types. Offline SQL generation now succeeds.
- JSONB defaults initially failed offline bulk rendering; settings now use fixed,
  typed SQL INSERT migration data. No service reads a hardcoded fallback.
- Reservation-sequence default comparison would consume numbers and report false
  drift if evaluated as two `nextval` calls. A narrow textual comparator avoids
  that side effect; real PostgreSQL regression now verifies the sequence remains
  unchanged and an altered default still fails the drift check.
- Live Alembic inspection exposed `AttributeError: 'Computed' object has no
  attribute 'arg'` before its legacy default callback ran. The comparison plugin
  handles the generated notification reference before ordinary defaults. It
  rejects generated-expression drift and preserves other comparisons. Initial
  duplicate registration during repeated Alembic environment loads was fixed by
  caching registration. Five new live cases passed; no existing test was weakened,
  removed or converted to a skip. No schema revision needed to change.
- Added FK-backed assistant book references and final reviewed-category storage
  so future AI/analytics features can retain real catalog/review relationships.
- Fixed Ruff formatting/import classification, strict typing, a seed output
  statement and seed connection disposal on early return/failure.
- Static test review corrected unequal executemany fields and fixtures that could
  hit an unrelated unique constraint before the intended FK check. Those original
  tests subsequently executed successfully against PostgreSQL.
- Generated schema reference uses PostgreSQL identifier shortening for long
  constraint names so documentation reflects compiled DDL names.
- Disk pressure was investigated separately from project code. Reclaimed only
  regenerable `work/npm-cache`, `work/uv-cache` and `frontend/.next/cache` inside
  the workspace after resolving/checking their paths. This was insufficient for
  stable Docker operation; no database volume was pruned or reset.

## 10. Final verification after storage recovery

### Environment failure resolved

The initial attempt reported:

```text
write /var/lib/docker/buildkit/containerd-overlayfs/metadata_v2.db: input/output error
commit failed: write /var/lib/desktop-containerd/daemon/io.containerd.snapshotter.v1.overlayfs/metadata.db: input/output error
Docker Desktop is unable to start
```

C: was independently observed full. The user expanded the partition to 300 GB
and recovered/updated Docker Desktop. At resumption, C: had 107,448,602,624 free
bytes (about 100 GB). Docker version/info/context/Compose checks passed through
approved escalation: client/server **29.8.0**, Compose **5.5.1**, Docker Desktop
**4.92.0**, desktop-linux, Linux x86_64 on WSL2. Existing PostgreSQL/Redis were
healthy. No volume reset, database deletion or recreation of the project was
needed. The previous storage failure is distinct from the Alembic project defect
described in section 9; both are resolved.

### Executed final commands and results

Commands ran from `C:\SmartLibrary` unless a directory is stated. `dev Compose`
below means `docker compose -f docker-compose.yml -f docker-compose.dev.yml`.
Docker operations used approved escalation. Test database cleanup deleted only
the uniquely named disposable database created by that test invocation.

| Executed command/check | Actual final result |
|---|---|
| `docker version`, `docker info`, `docker context ls`, `docker compose version` | Responsive Linux engine; versions above |
| `dev Compose build backend` | Passed, including final build after the comparison fix |
| `dev Compose run --rm database python -m app.db.manage upgrade` | All three revisions applied to development; restricted runtime grants applied |
| `dev Compose run --rm database python -m app.db.manage check` | Initially exposed the Computed callback defect; after correction passed at `0003_defaults_and_guards (head)` with no new upgrade operations; passed again after final restarts |
| `dev Compose run --rm database python -m app.db.manage seed` twice | First seed persisted; second preserved existing data/passwords |
| Read-only live inspector through `dev Compose run --rm -T database python -` | Actual PostgreSQL catalog, all 27 row counts, constraints/indexes/types/triggers, settings, password/QR material and role flags/grants verified; results in section 4 |
| `docker compose --profile testing build database-tests` | Final test image built successfully |
| `docker compose run --rm database-tests` | Fresh-database migration round trip and drift passed; original suite first passed 49/49; final suite passed **54/54, zero skips**, including all 41 PostgreSQL-backed cases; disposable database removed |
| `uv lock --project backend --cache-dir C:\SmartLibrary\work\uv-cache` | Lock synchronized with Alembic API minimum; locked Alembic remains 1.20.0 |
| `backend/.venv/Scripts/ruff.exe check --config backend/pyproject.toml backend/app backend/alembic scripts` | Passed |
| Same Ruff scope with `format --check` | Passed; 75 files already formatted |
| From backend: `.venv/Scripts/mypy.exe --cache-dir var/mypy-cache` | Passed; 57 source files |
| From backend: `.venv/Scripts/python.exe -m pytest -q` | **13 passed, 41 skipped** outside the isolated database environment; these skips are not counted as passes and all 41 executed in the Docker PostgreSQL run |
| `backend/.venv/Scripts/python.exe scripts/export_openapi.py --check` | Passed; health contract unchanged |
| `backend/.venv/Scripts/python.exe scripts/export_schema_reference.py --check` | Passed; reference matches models |
| `docker compose config --quiet`, `dev Compose config --quiet`, and base `--profile testing --profile database config --quiet` | All passed |
| `docker compose build backend` | Final runtime image built successfully |
| `docker compose up -d --wait --wait-timeout 180` | All six runtime services healthy |
| `backend/.venv/Scripts/python.exe scripts/verify_stack.py --test-outages` | Runtime routing, liveness, readiness, served OpenAPI, Celery ping, non-root processes and private networking passed; PostgreSQL/Redis outages returned readiness 503 while UI/liveness stayed 200; recovery returned readiness 200 and all six services healthy |
| Final `dev Compose build backend`, then `dev Compose up -d --wait --wait-timeout 180` | Final development image/startup passed; all six healthy |
| `backend/.venv/Scripts/python.exe scripts/verify_stack.py --dev` | Final development health/routing/contracts/worker/networking passed; no published PostgreSQL/Redis host ports; only Nginx at `127.0.0.1:8080` |
| From frontend: `$env:PLAYWRIGHT_CHANNEL='msedge'`; `npm run test:e2e` | **3 passed in 4.5s** against final development stack: Kazakh shell, frontend liveness, Nginx API/readiness/docs |
| Read-only SQL through the running backend container | Current role is `smartlibrary_app`; 12 books and 24 copies survived restarts; zero leftover isolated test databases |
| Final `dev Compose ps` | Frontend, backend, PostgreSQL, Redis, Celery worker and Nginx all running/healthy |
| Source-baseline/hash and relative Markdown link checks | All 154 baseline files present; 68 protected implementation files unchanged; Master Specification hash unchanged; links passed across 18 documentation files |

The final database run took 1.91 seconds for pytest, excluding migration setup.
It retained the existing non-failing Starlette/httpx TestClient deprecation
warning. The native run initially encountered a sandbox cache-write warning;
rerunning through approved escalation removed that warning. Playwright emitted
the existing terminal color-environment warning. An initial offline lock refresh
lacked cached package metadata; the registry-assisted lock command succeeded.
None required removing or weakening an assertion.

Final image manifest checkpoints:

- Test: `sha256:545525bd380225f1bf9397babdca07e1ff9130db06ac498f7c56a2516c675d18`.
- Runtime backend: `sha256:40cb02dccf21f0697300c54c538e5e80d937f8a7f4921f63caf991713400150b`.
- Development backend: `sha256:b27e515bb9c3af312c9d4373d5fbfbea2a193a7ca42dbf51e8e26e21a49af4e9`.

Evidence is saved in ignored `work/logs/phase2-final-*` files: migrations,
head/drift, seed/repeat, PostgreSQL tests, native pytest, builds/startup,
runtime/development stack checks, running role and browser results. The complete
read-only catalog inspection is `work/logs/phase2-live-database.json`.
Static metadata/offline rendering and native skips are explicitly separate from
the actual PostgreSQL results above. The foundation stack script still prints
its original "PHASE 1 stack verification passed" label; it was executed here as
a PHASE 2 regression against the new runtime database credentials.

No external requirement remains for PHASE 2. Keep Docker Desktop running and
retain the private `.env` and persistent volumes. LLM credentials, a selected
embedding model, email delivery and production TLS remain dependencies of their
later feature/deployment phases, not unfinished PHASE 2 verification.

## 11. Specification integrity and readiness

`MASTER_SPECIFICATION.md` remains 134,394 bytes with SHA-256:

```text
DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61
```

The baseline and checked hash match. The file was not modified.
Final integrity evidence is saved in `work/logs/phase2-final-source-integrity.json`.

**PHASE 2 COMPLETE — READY FOR PHASE 3.** Live migrations, schema/seed/grant
inspection, drift, fresh-database round trip, all PostgreSQL cases and prior
stack regression passed. The existing schema/migrations, restricted runtime
connection and session-storage foundations are ready for the authentication
phase. No authentication, token rotation, HTTP RBAC or later circulation service
was implemented here. The remaining PHASE 3 gate is explicit user instruction;
re-read its specification requirements and inspect this baseline before starting.
