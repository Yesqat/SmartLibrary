# Required test coverage

Paths below are relative to the repository. Backend names without another prefix
are in backend/app/tests/database/domain; all database cases execute on isolated
PostgreSQL, with Redis and actual pinned embeddings where required. See phase
reports and final acceptance matrix for execution evidence, not this index alone.

| Specification scope | Tests |
|---|---|
| Registration, login, password, expiry, refresh/replay, blocked/inactive, RBAC, CSRF | database/test_auth.py; test_auth_security.py; test_hardening.py; domain/test_hardening.py |
| Catalog metadata, copy separation, safe archive, constraints, uploads | test_catalog.py; test_reservation_catalog.py; database/test_schema.py; native test_images.py |
| Exact/ISBN/metadata/fuzzy ranking, filters, pagination, autocomplete, event ownership | test_search.py |
| READY/WAITING, duplicate, QR owner, cancel/FIFO/idempotence, live settings, overdue | test_reservations.py |
| Verify never issues, separate explicit issue, expired/completed/tampered QR, limits, receipts | test_reserved_issue.py |
| Direct issue, normal/damaged/lost, return queue, terminal retries, Reader cannot return | test_circulation.py |
| Two Readers/one copy; simultaneous duplicate/cancel | test_simultaneous_reservation_serialization; test_concurrent_cancel_advances_once |
| Two issuers/one copy; same Reader across books | test_concurrent_reserved_issue; test_concurrent_direct_issue; test_cross_book_issues_share_reader_limit_lock |
| Reservation vs issue; return vs cancel | test_concurrent_reservation_vs_direct_issue; test_concurrent_return_and_ready_cancel_preserve_fifo |
| Expiry race, rollback, return vs overdue job, eligibility recovery | test_scheduled.py |
| Worker delivered through Redis, actual restart, no duplicate notification | test_worker_delivery.py |
| Favorites, preferences, notifications/ownership, profile/avatars, Reader loans/history | test_reader.py |
| Staff dashboard, camera fallback API, operational readers/overdue | test_librarian.py |
| Admin role/status/session revocation, last Admin race, settings/versioning, read-only audit | test_admin.py |
| Real vectors, stale source invalidation, filters, live availability, exact hybrid priority | test_semantic.py |
| Cold start/preferences, canonical popularity, real similarity/profile, consumed exclusion, receipts/impressions/click ownership | test_recommendations.py; native test_collaborative.py |
| Actual classifiers, known categories, multi-label review, stale reviews/provenance, reproducibility | test_categorization.py; native test_categorization.py; ml/evaluation/benchmark_search.py; app.ai.categorization.training |
| Tool identity, injection, current facts, conversation ownership, provider timeout/invalid/outage, concurrency/revocation | test_assistant.py; native test_assistant_provider.py |
| SQL metric/date/timezone/zero-bucket/CTR definitions | test_analytics.py; native test_analytics_dates.py |
| All four report types, both formats, authorization, range/limit, typed XLSX, escaped embedded-font PDF | test_reports.py; native test_reports.py |

## Frontend behavior (PART 189)

frontend/tests/auth-form and auth-session cover forms, pending submissions and
memory-only sessions. catalog/search cover availability, filters, safe errors and
retry. reservations/pickup cover status/QR visibility, cancellation and explicit
issue confirmation. physical-circulation covers inspected return condition and
duplicate prevention. reader covers favorites, notification state/navigation,
overdue and no Reader return action. admin covers role confirmation, integer
setting bounds/empty/fraction rejection, optimistic conflicts and immutable audit.
camera covers permission denial, unavailable device and late permission cleanup.
AI/recommendation/analytics/report tests cover grounded cards, failures, measured
impressions, empty metrics, typed downloads and rendering. No snapshot-only gate.

## Required browser scenarios (PART 190)

| E2E | Executable file and behavior |
|---|---|
| 1 | auth.spec.ts: public READER registration/login/dashboard, refresh across tabs, password/logout, all role layouts |
| 2 | reservations.spec.ts: search → details → reserve → READY/WAITING, private QR, mobile layout |
| 3 | pickup.spec.ts: verify → still READY/RESERVED with zero issue requests → explicit issue → COMPLETED/BORROWED → Reader My Books |
| 4 | physical-circulation.spec.ts: inventory lookup → GOOD return → Reader active list empty and returned book in history |
| 5 | physical-circulation.spec.ts: A/B WAITING → return gives A READY/B WAITING → A cancels → B READY |
| 6 | admin.spec.ts and analytics.spec.ts: roles/status/session invalidation, real metrics, settings, immutable audit |

Additional browser files cover real camera decoding/manual fallback, catalog
editing, lexical/semantic/hybrid search, recommendations/impressions, both actual
category methods/human review, AI outage persistence, analytics, PDF/XLSX downloads,
CSP parser injection and infrastructure routing. The controlled camera supplies
pixels to the real scanner; provider mocks occur only at the external LLM boundary.

## Isolated browser execution

docker-compose.e2e.yml with `-p smartlibrary-e2e`, the base/dev configurations and
ignored work/e2e.env uses port 8081, separate PG/Redis/uploads and read-only shared
pinned model artifacts. The E2E database is independently migrated and seeded.
scripts/run_e2e.py runs every test file, stopping on failure and saving per-file logs.
It initializes only its dedicated Redis test namespace before each file, with
unchanged policy limits and no resets inside a file. It refuses a non-test app or
another namespace. Development/production rate counters and data are untouched.
Public auth endpoints and rate-limit rejection remain real, separately tested.

Use scripts/run_e2e.py `<name>.spec.ts` for targeted reruns. Do not point it at the
development stack, remove assertions, or substitute API mocks for domain flows.
The separate test stack can be stopped to release memory without deleting volumes.

## Final additions and evidence

PHASE 22 adds pages.spec.ts (four roles, 56 actual route visits) and
 test_acceptance_m_two_turns_use_live_copy_count_and_exact_owned_due_date.
The complete 358-case backend run plus that additional targeted case account for
all 359 current tests with zero skips. Frontend 70, Edge 28, production TLS Chromium
1 passed. FINAL_ACCEPTANCE_MATRIX.md maps each scenario to saved final evidence.
