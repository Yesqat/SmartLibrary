# Final project reviews

Completed 2026-09-28 (Asia/Qyzylorda). The complete Master Specification was read
before PHASE 4; PARTS 199–200 and every final review were re-read for PHASE 22.
This is an implementation/code/test review, not independent penetration testing.

## Code and architecture

Reviewed active FastAPI routes, services/repositories, models/migrations,
storage, AI/tool boundaries, Celery tasks, typed client, role layouts and feature
components against the final contract. Backend remains a modular monolith.
Removed eight unreferenced empty packages left by scaffolding; actual services
were retained. Replaced obsolete “future functionality” package/README text.
No business architecture, valid test or production behavior was weakened.

An explicit scan of 268 production Python/TS/TSX files found no TODO, FIXME,
NotImplementedError or console.log/debug. Additional placeholder/fake/mock scans
found legitimate HTML input placeholders; test HTTP/external-provider doubles
were reviewed separately. No production mock API, hardcoded availability/analytics,
fake encoder or synthetic production AI response was found.

Repository candidate files were compared against actual private configuration
secret values without printing those values; no match was found. Git ignores
private environments, dependencies, caches, model artifacts, uploads, TLS keys and
dumps. No commit, push, remote or broad filesystem/Docker cleanup was performed.

## Database and concurrency

Five migrations agree with models and actual PostgreSQL at
0005_reservation_reminder. Live and freshly initialized databases were inspected:
27 UUID PKs, 16 enums, 48 FKs, 31 unique constraints, 60 checks, 143 domain indexes
plus Alembic, timezone-aware timestamps and required extensions. Model-space
constraints enforce 768-dimensional E5 vectors in the selected versioned space.
BOOK/COPY, reservation owner/title/copy and borrowing reservation links agree.

Runtime role has no DDL/superuser/bypass privilege; historical/audit guards remain.
Only new disposable databases were used for downgrade/restore tests.
Real concurrent reservation/issue/return/cancel/expiration tests passed, including
cross-book Reader limits and return versus job/cancellation. Shared transaction
boundaries, row locks, constraints and current-state rechecks prevent double issue.

## Security

Argon2id, safe auth errors, minimal validated JWT claims, hashed rotating refresh
families, replay/session revocation, memory-only access tokens, Origin/CSRF and
Redis limiting were exercised. Public registration rejects privileged fields.
Current database role/status is authoritative; Admin role/status edits revoke
sessions. Ownership tests cover reservations, notifications, loans and conversations.

QR secrets are opaque, hashed plus encrypted for owned recovery, lifecycle-bound
and cleared at termination. Verification is read-only; session-bound confirmation
precedes explicit Librarian issue. Expired/completed/cancelled credentials fail.
Reader cannot physically return; Librarian cannot promote roles or change settings.

Uploads validate permission, size, MIME and actual decoded JPEG/PNG/WEBP content,
generate filenames and re-encode outside executable directories. SQL filters/sorts
are validated; queries are parameterized. Errors omit technical exception details.
Audit/report DTOs exclude auth/QR/API secrets and audit history has no edit UI.

Actual browser parser-injection and production TLS/session tests passed.
Per-request nonce CSP blocks untrusted scripts; production has no unsafe-eval.
Inline styles remain allowed for charts/components. Nginx overwrites forwarding
headers, enforces canonical host/origin, TLS 1.2/1.3, HSTS, request limits and
safe error handling. PostgreSQL/Redis have no published host ports.

## AI and ML

Local E5 small/base benchmarking, pgvector queries and RRF hybrid retrieval are
real. Exact title/ISBN priorities, filters and copy-derived availability passed.
The exact Kazakh acceptance prompt ranks Clean Code then Python Crash Course;
this is recorded honestly, not described as perfect beginner-intent ranking.

Popular/similar/personal recommendations use actual events/circulation/preferences/
vectors. Cold start works. Rendered impressions and attributed clicks define CTR.
Collaborative evaluator reports INSUFFICIENT_DATA, with no fabricated metrics.

Both multi-label categorization methods are real, use existing categories and
require human review. Two final training runs reproduced coefficients, thresholds,
metrics and artifact revision. Only two held-out books exist: classical test F1=0,
embedding test micro F1=0.666667, macro F1=0.2. General accuracy is not established.

The assistant has nine bounded read-only backend tools; authenticated identity
cannot be supplied by the model. Tool facts and validated book references determine
responses; no arbitrary SQL/circulation writes or invented identifiers.
Exact two-turn availability/due-date, injection/ownership, timeout/invalid-response,
concurrency and failure cases passed. Only the external provider was scripted.
Live provider inference remains unverified until real credentials/model access exist.

## UI

All required public, Reader, Librarian and Admin surfaces are mapped in UI_SITEMAP.md.
Four browser sweeps completed 56 route visits using real APIs and checking headings,
loading completion, application errors and JavaScript failures. The initial assertion
mistook Next.js's empty route announcer for an error; it was scoped to the application
main landmark. Domain error assertions remain intact.

Twenty-eight Edge cases verify auth, search/reservation/QR, explicit issue,
physical return/history/FIFO, Admin actions, camera decoding/manual fallback,
recommendations, ML review, AI unavailability, analytics, downloads and CSP.
Component tests cover form confirmation, duplicate prevention, safe errors/retry,
empty/loading states, permission states and camera failures. Responsive/label/
landmark checks passed in relevant browser/component cases; no formal external
accessibility certification is claimed. No unrelated visual redesign was performed.

## Infrastructure, reports and recovery

Runtime/dev/test images build. Eight services are healthy in runtime, development,
production-mode HTTPS and the fresh isolated rehearsal. Beat/default/ML workers
have real health checks. Dependency outage verification returned readiness 503,
kept liveness/UI 200 and recovered readiness to 200. Only Nginx publishes ports.

The final fresh project used independent secrets and empty PG/Redis volumes:
migrate → seed six users/12 titles/24 copies → generate 12 real vectors → start
and verify every service, actual schema and semantic/hybrid search. Pinned weights
were reused from the local cache; no fresh internet download or remote Git clone
is claimed. Primary data was preserved and the primary development stack restored.

All four PDF/XLSX report pairs were generated from actual development rows and
reopened. Seven rendered PDF pages were visually inspected: readable Kazakh/
Cyrillic, no clipped content, repeated table headings and page numbering. Typed
numeric/date XLSX cells and formula safety passed. Range/summary/authorization
checks use PostgreSQL fixtures. Poppler's optional external mapping-file warnings
on the Windows Unicode path did not prevent rendering embedded report fonts.

Actual pg_dump plus image/artifact archives were hashed and restored into a new
random database. Extensions, head/drift, restricted-role reads and real row counts
passed. Only that disposable restore database was removed. Docker volumes are
not represented as backups; off-site protected storage remains an operator duty.

## Tests and final boundaries

The complete backend gate passed 358 tests; the subsequently added exact assistant
acceptance case passed separately. All 359 current cases therefore executed with
no skips. The separate 98 native cases are included in that count, not additional.
Seventy component, 28 Edge and one production TLS Chromium case passed.
Ruff/format, mypy, frontend lint/format/types/build, contracts and all Compose
configurations passed. Dependency deprecation warnings remain non-failing and are
recorded in logs; no valid assertions were disabled.

FINAL_ACCEPTANCE_MATRIX.md identifies each A–X result and exact local evidence.
Remaining deployment requirements: live LLM credential/model/quality checks, public
domain/trusted certificate and protected off-site backups. Optional email reset,
bulk import and continuous decay are clearly not advertised. No mandatory internal
feature is left as a critical TODO or mock.
