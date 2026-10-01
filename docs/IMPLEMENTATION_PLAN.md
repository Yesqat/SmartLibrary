# Implementation order and dependencies

Status: PHASES 0–3 complete and preserved. The user authorized autonomous
PHASES 4–22 in order; PHASES 4–22 are complete (their reports record the gates).
FINAL_IMPLEMENTATION_REPORT.md and FINAL_ACCEPTANCE_MATRIX.md record executed
final results and external-provider/deployment limitations. No further phase is authorized.
Each PHASE_N_REPORT records its completion gate before the next phase.
Source: PART 198 together with all PARTS 1–200 and final instructions. Re-open
relevant sections/dependencies and inspect current code before every phase.

## Ordered gates

All phases depend on completed compatible earlier foundations; the table highlights dependencies that are easy to miss. Part references are navigation aids, not exemptions from the rest of the contract.

| Phase | Scope from PART 198 | Key dependencies and exit evidence |
|---|---|---|
| 0 | Repository inspection and architecture documents | Complete specification read, workspace inventory, design, dependencies and honest readiness report |
| 1 | Project structure + Docker development environment | PARTS 3–4, 128–132, 170–182, 193–197; version/lockfile decisions, safe config, executable service scaffolding, Compose/build/health checks; no domain completion claims |
| 2 | PostgreSQL + pgvector + Alembic + core schema | PARTS 13–28, 117–125, 133, 137–143, 158–161, 166; core entities plus settings/audit/session foundations; extension/constraint/empty-DB migration verification |
| 3 | Authentication + sessions/tokens + RBAC | Schema and typed config; PARTS 5–8, 30, 41–57, 163–166; public READER registration, revocation, ownership and permission tests |
| 4 | Catalog + authors + categories + publishers + physical copies | Auth, schema, storage validation, state boundaries; PARTS 13, 31, 52, 119, 127, 139, 142–143, 156–157, 167; real metadata/copy APIs and compatible UI |
| 5 | Standard/fuzzy search + filters + pagination | Catalog, pg_trgm, typed client; PARTS 23, 32, 58–59, 134–136, 154–156, 185; ranking/filter tests and actual search event capture |
| 6 | Reservation system + queue + QR generation | Catalog/auth/current settings/notification/audit foundations; PARTS 14–16, 20, 33, 46, 50, 137–140, 158–162; transactional FIFO, cancellation and expiry service, secure QR lifecycle and race tests |
| 7 | Librarian QR verification + issue workflow | Reservation invariants, borrowing models and staff permissions; PARTS 15, 17–18, 34, 46, 97, 137–141; separate verify/issue and revalidation with limits/overdue |
| 8 | Direct issue + return + damaged/lost workflows | Shared queue/transition service and locking; PARTS 18–20, 35, 98–99, 137–143, 183–184; atomic return/reallocation, conflict and repeat-request tests |
| 9 | Reader pages + favorites + notifications + profile | Auth, catalog/search, circulation; PARTS 6, 10, 21–26, 36, 85–95, 112–116, 161–168; reader ownership, READY QR, history and real notification state |
| 10 | Librarian Panel | Phases 4–9 workflows; PARTS 7, 11, 96–104, 112–116; camera/manual preview, explicit issue/return and reader operations |
| 11 | Admin Panel + settings + audit logs | Persisted settings/audit already used by services; PARTS 8, 12, 28, 39, 105–111; management, role/status changes and immediate rule effects; later analytics/AI pages complete in owning phases |
| 12 | Embeddings + Semantic Search + Hybrid Search | Catalog/search, vector schema, model benchmark, worker infrastructure; PARTS 60–62, 123, 125, 154–156, 185; real multilingual retrieval, re-embedding and filtered ranking |
| 13 | Recommendation System | Interactions/favorites/loans, category preferences, vectors; PARTS 22, 25, 37, 63–68, 150–153, 186; real recommendation modes, source tracking and rendered impressions |
| 14 | Auto Categorization + ML training/evaluation | Categories, multilingual embeddings, labeled dataset and review UI; PARTS 69–73, 101, 124–125, 187; reproducible baseline/comparison, reviewed persistence and truthful metrics |
| 15 | AI Librarian Assistant | All safe catalog/search/personal/rules tools, ownership, LLM adapter; PARTS 38, 54–55, 74–84, 95, 126, 188; grounded structured responses, explicit reservation confirmation and outage tests |
| 16 | Analytics + search/recommendation analytics | Real events captured since originating phases, prediction reviews and AI telemetry; PARTS 105, 107–108, 144–146, 150–153; shared SQL metric definitions and DB comparisons |
| 17 | PDF/XLSX Reports | Shared analytics queries and admin auth; PARTS 109, 147–149; inventory/borrowing/overdue/reservation reports, actual file validation and Cyrillic rendering |
| 18 | Celery/Redis scheduled/background workflows | Worker infrastructure and already testable domain job services; PARTS 27, 57, 123, 138, 161; scheduling, durable retry, deduplication and restart/expiration tests |
| 19 | Security hardening | Controls installed with each feature; PARTS 41–57, 163–168, 176, 191; cross-system threat review and remediation, no deferral of basic auth/security until here |
| 20 | Backend/frontend/E2E tests | Incremental tests already present; PARTS 183–192 and 200; complete regression, PostgreSQL races, UI, real ML and external-boundary outage coverage |
| 21 | Nginx + production-like deployment | Working Compose and secure runtime; PARTS 178–182, 193–195; TLS/proxy/isolation, health/logging and backup/restore verification |
| 22 | Documentation + final verification | All phases and PARTS 170–177, 199–200; current docs/commands, A–X evidence, every final review and deliverable; no unsupported completion claims |

## Dependencies spanning phases

- PHASE 2 prepares settings and audit persistence; PHASES 6–8 use validated settings and audit events before the PHASE 11 admin editing UI exists.
- PHASE 6 implements queue/expiry domain rules and their tests. PHASE 18 wires periodic execution and recovery, without duplicating queue logic. Incomplete scheduling is reported honestly until verified.
- PHASE 1 provides worker infrastructure; PHASE 12 can execute actual embedding tasks on it. PHASE 18 completes scheduled workflows and restart tests.
- PHASES 4–5 and 6–9 capture actual view/search/click/favorite/reserve/borrow events. PHASE 13 captures actual impressions; PHASES 14–15 capture reviews/provider usage. PHASE 16 cannot reconstruct missing historic telemetry.
- PHASE 11 cannot claim fully working future AI/analytics reports. Finish those surfaces in PHASES 14–17, with explicit status in each phase report; no fake KPI cards.
- Maintain schemas/migrations/contracts/docs in the same feature change. PHASE 20 and PHASE 22 consolidate existing evidence rather than starting tests/docs from zero.
- Seeds are introduced as executable features need demonstration/test data, remain realistic and labeled development data, and gain reproducible ML initialization later. Never use seed constants as dashboard results.

## Scope and conditional requirements

All unconditional requirements remain in scope. For specification-conditioned features, preserve their stated conditions: meaningful collaborative filtering depends on data; time decay is optional with an extensible boundary; email reset requires real infrastructure; bulk import is optional. Record an explicit decision and evidence when reaching each owning phase. No conditional statement permits replacing mandatory local ML or circulation with fake behavior.

At each exit record implemented behavior, files, migrations, endpoints, UI, tests, exact commands, results and external limitations. Fix phase-affecting errors before advancing. A limitation entry records requirement, reason, dependency/configuration, implemented portion and unverified remainder.
