# Final acceptance matrix — PART 200

Verification date: 2026-09-28, Asia/Qyzylorda. Paths below are repository-relative.
DB means backend/app/tests/database/domain; browser means tests/e2e.
The Master Specification remains unchanged. Status applies to the scope explicitly
described; a provider-boundary test is never represented as live external inference.

## Evidence keys

- **D:** work/logs/final-database.txt — complete run, 358 passed, zero skips.
- **M:** work/logs/final-assistant-scenario-m.txt — subsequently added exact two-turn
  acceptance case, 1 passed, zero skips. Thus all 359 current backend cases executed;
  358 were in the consolidated run and the additional case was targeted.
- **B(name):** work/logs/final-e2e-name.spec.ts.txt — 28 Edge cases in 18 files.
- **N/F:** final-native-tests.txt (98, also included in D), final-frontend-tests.txt
  (70), final-backend-checks.txt, final-helpers-lint.txt, final-frontend-checks.txt,
  final-docs-format.txt, final-frontend-build.txt, all under work/logs.
- **S:** final-live-schema.txt, final-development-schema.txt,
  final-development-seed.txt, final-clean-schema.txt, final-clean-drift.txt.
- **I:** final-runtime-build.txt, final-runtime-backend-final-build.txt,
  final-runtime-stack.txt, final-development-build.txt, final-development-stack.txt,
  final-production-checks.txt, final-production-browser.txt, final-compose-config.txt,
  final-clean-stack.txt and final-primary-stack.txt.
- **ML:** final-search-benchmark.txt, final-categorization-a.txt/-b.txt,
  final-artifact-checks.txt, final-semantic-live.txt, final-clean-semantic.txt,
  final-clean-vectors.txt and final-recommendation-evaluation.txt.
- **R:** final-report-generation.txt, final-artifact-checks.txt and
  work/final-report-verification/ (eight files, seven inspected page renders).
- **W:** final-backup-restore.txt — real dump restored into a disposable database.

Every referenced log is local under work/logs unless another path is shown.
Logs/exports are ignored and may contain development data; do not publish them
without review. Phase reports preserve concise durable results.

| Scenario | Implementation / API | Executed tests and observed behavior | Status / evidence |
|---|---|---|---|
| A — New Reader | services/auth; /auth/register, /auth/login; frontend/features/auth | test_auth registration/allowlist/RBAC; browser auth and reservations. Registration yields READER, dashboard/catalog/search work, privileged body rejected. | PASS — D, B(auth), B(reservations) |
| B — Available reservation | services/reservations; POST /reservations, owned QR | test_ready_qr_recovery_copy_state_and_no_loan; browser reservations. Assigned copy RESERVED, reservation READY, private QR displayed, no borrowing. | PASS — D, B(reservations) |
| C — QR issue | borrowings/proof.py and service.py; /librarian/qr/verify and explicit issue | test_reserved_issue; browser pickup/camera. Verification keeps READY/RESERVED and makes no issue request. Explicit confirmation creates loan/COMPLETED/BORROWED; Reader My Books shows it. | PASS — D, B(pickup), B(librarian) |
| D — FIFO queue | reservations/service.py and borrowings/service.py | test_return_assigns_same_copy_to_first_waiter; browser physical-circulation. A READY, B WAITING after return; A cancellation advances B. Owned notification asserted in DB cases. | PASS — D, B(physical-circulation) |
| E — Expiration | notifications/scheduled.py; Celery circulation sweep | test_expiration_reuses_copy_fifo_clears_qr_and_is_repeatable; concurrent expiry/rollback. EXPIRED clears old QR, same copy goes to next eligible waiter, notification deduplicates. | PASS — D |
| F — Return | borrowings/service.py; inventory lookup and explicit return | test_direct_issue_lookup_return_and_repeat_cannot_change_later_loan, queue case; browser physical-circulation. returned_at/history updated; AVAILABLE or RESERVED according to queue. | PASS — D, B(physical-circulation) |
| G — Damaged | copy state machine and borrowing return | test_damaged_return_never_enters_queue_or_availability; component return tests. Loan RETURNED, copy condition/status DAMAGED, unavailable. | PASS — D, F |
| H — Lost | borrowings/service.py; /librarian/borrowings/{id}/lost | test_lost_is_terminal_unavailable_and_idempotent. Loan/copy LOST; repeated request safe; invalid terminal transitions fail. | PASS — D |
| I — Overdue restriction | settings/policy.py; reservation and both issue paths | test_live_settings_and_due_at_overdue, reserved/direct issue limits. due_at blocks independently of worker status; settings change behavior. | PASS — D |
| J — Semantic search | ai/embeddings and repositories/vector_search.py; /search?mode=semantic | Real encoder/pgvector tests and exact Kazakh prompt from PART 200. Live top two: Clean Code, Python Crash Course; availability checked against SQL. Fresh seeded stack repeats query. | PASS — D, B(semantic), ML |
| K — Recommendations | ai/recommendations; /recommendations/me, popular/similar | test_recommendations real profile/cold start, consumed exclusion, actual vectors and owned attribution; browser rendered impression/click. No fabricated collaborative quality. | PASS — D, B(recommendations), ML |
| L — Categorization | ai/categorization; /ai/categorize and review | Both real methods, known categories, scores/provenance, human modification and transactional review; browser both-method review. Two independent training runs reproduced artifacts/metrics. | PASS — D, B(categorization), ML |
| M — AI Librarian | ai/assistant tools/orchestration/provider; owned conversation messages | Exact “Clean Code қазір бар ма?” then “Мен оны қашан қайтаруым керек?” passed with actual copy count and exact authenticated loan due_at; same conversation retained. Only external provider scripted. | PASS at the permitted controlled provider boundary — M/D. Live provider BLOCKED: configure LLM_PROVIDER, LLM_MODEL, LLM_API_KEY and verify actual model/tool selection. No live answer claimed. |
| N — Security | core/security, permissions/ownership, every protected route | test_auth, test_hardening, ownership/QR/assistant injection cases; Reader/Admin/Librarian denials, privilege escalation, expired/completed QR. Actual CSP and TLS session tests. | PASS — D, B(auth), B(security), I |
| O — Analytics | services/analytics; /admin/analytics/* | test_analytics compares persisted counts/trends/due_at/search/CTR with SQL, zero buckets/timezones; real Admin charts/browser. | PASS — D, B(analytics) |
| P — Reports | services/reports; POST /admin/reports | All four types × PDF/XLSX generated/reopened. Date/summary/authorization tests passed. Current DB exports: 27 inventory, 10 loans, 1 overdue, 16 reservations; seven PDF pages visually verified. | PASS — D, B(reports), R |
| Q — Settings | administration/service.py, settings/policy.py; PATCH /admin/settings | Admin validation/versioning plus circulation/reminder tests. New due dates/holds/limits/reminders use updated settings without restart; historical dates stay intact. | PASS — D, B(admin) |
| R — Concurrent reservation | Book/User locks and partial unique constraints | test_simultaneous_reservation_serialization: two eligible Readers, one copy → exactly one READY and one WAITING, no duplicate assignment. | PASS — D |
| S — Concurrent issue | borrowings/service.py, idempotency, locks/constraints | test_concurrent_direct_issue and test_concurrent_reserved_issue: one active loan, competing distinct request conflict, same-request retry safe. Cross-book limits and reservation-vs-issue also tested. | PASS — D |
| T — Background | workers/tasks/scheduler and notifications/scheduled.py | Scheduled expiry/FIFO/due-soon/overdue/dedup cases; test_worker_delivery starts real Celery through Redis and restarts it without duplicates. Beat/default/ML health checked. | PASS — D, I |
| U — AI failure | provider unavailable contract; independent core services | Provider timeout/invalid/outage cases and browser unconfigured-provider state/history. Entire real browser suite runs with LLM unavailable while registration/search/QR/issue/return/admin remain usable. | PASS — D, B(assistant), all B |
| V — Docker deployment | Dockerfiles, Compose, Nginx, operator/model CLIs | Runtime/dev/test builds, eight healthy services, private PG/Redis, proxy/health/TLS/outage recovery. Fresh independent local project applies migrations/seeds and generates 12 real vectors from pinned cached weights. | PASS for reproducible local setup — I, final-clean-migration/seed/vectors logs. Clone/public hosting not executed: Git publication is explicitly deferred. |
| W — Fresh database | five Alembic revisions, manage.py, verify_database.py | D creates empty databases and tests upgrade/downgrade/upgrade/head/drift/seed. Fresh project independently verifies actual extensions, UUID/FK/check/index/enums/roles/data; backup restore additionally passes. | PASS — D, S, W |
| X — Build/test | backend/frontend tests and all deployment commands | Lint/format/mypy/contracts/native/full PG+Redis/components/production build/28 Edge/1 TLS browser; runtime/dev/test Docker builds and configuration/startup checks. | PASS — D/M/N/F/B/I |

## Scope boundaries

Public TLS/domain, remote Git clone/publication and live LLM credentials are not
fabricated. Local production-mode TLS is real and certificate-validated; it does
not constitute a public deployment. PART 200's missing-provider policy is applied
to M: internal functionality and failure safety pass; external inference remains
explicitly unverified. Optional email reset, bulk import and continuous time decay
are not presented as active features. Collaborative evaluation honestly reports
INSUFFICIENT_DATA; content-based recommendations are verified.
