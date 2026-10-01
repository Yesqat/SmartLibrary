# API contracts

PHASE 13 implements GET books/popular, books/{id}/similar, recommendations/me;
POST recommendations/impressions and recommendations/impressions/{id}/click.
Bounded typed results include real Book DTOs, reason codes and Reader-only signed
delivery receipts. See RECOMMENDATIONS.md for visibility/ownership/idempotence semantics.

PHASE 12: `GET /api/v1/search` accepts `mode=standard|semantic|hybrid`; dedicated
GET `/api/v1/search/semantic` and `/api/v1/search/hybrid` share the same validated
filters/pagination. SearchPage adds `indexing_pending`; events/clicks retain actual
mode attribution. Model unavailability returns safe SEMANTIC_SEARCH_UNAVAILABLE/503.
OpenAPI/generated TypeScript are synchronized. See SEMANTIC_SEARCH.md.

## PHASE 11 Admin additions

All paths under `/api/v1/admin`: GET `/dashboard`, `/users`, `/users/{id}`,
`/librarians`, `/inventory`, `/borrowings`, `/reservations`, `/settings`,
`/audit-logs`; PATCH `/users/{id}/role`, `/users/{id}/status`, `/settings`.
All enforce explicit Admin permissions, bounded pagination/filter validation and
safe DTOs. Mutations require Origin and Redis limits. Settings accept a nonempty
unique `changes` list of key, strictly typed value and expected_updated_at;
updates are atomic and reject stale versions with SETTINGS_CONFLICT. Role/status
changes revoke sessions, preserve the last ACTIVE ADMIN and active Reader
circulation. Audit is read-only. See ADMIN.md and generated OpenAPI for contracts.

## PHASE 10 Librarian additions

GET `/api/v1/librarian/dashboard`, `/readers/{id}`, `/readers/{id}/borrowings`,
`/reservations`; POST `/reservations/verify-number`. Existing Reader list adds
status/UUID search; overdue adds q/minimum_days/order filters. All Librarian-only,
safe DTOs and bounded pages. Manual verification never issues. See LIBRARIAN.md.

## PHASE 9 Reader additions

- GET `/api/v1/favorites`: own page; GET/POST/DELETE `/{book_id}`: state/add/remove.
- GET `/api/v1/notifications`; PATCH `/{id}/read`; POST `/read-all`.
- GET `/api/v1/reader/summary`: owned SQL counts and nearest due date.
- GET/PATCH `/api/v1/users/me`: safe profile; names/phone allowlist, email read-only.
- GET/PATCH `/api/v1/users/me/preferences`: real categories, optional atomic replacement.
- POST/DELETE `/api/v1/users/me/avatar`: validated image lifecycle.
- Reservations `/me` adds optional `active` filter; active loans sort by due date.

See READER.md and generated OpenAPI for contracts, ownership and bounded paging.

All domain, AI, analytics and report contracts are implemented and exported in
openapi.json. API_ENDPOINTS.md lists all 112 operations. Sources:
PARTS 29–40, 131–135, 154, 163–170. All specified minimum endpoints remain required.

## Current endpoints

PHASE 6 adds Reader create/list/detail/cancel and owner QR endpoints. See
[RESERVATIONS.md](RESERVATIONS.md) for the exact contract, limits and ownership.
PHASE 7 adds separate Librarian QR verification and reserved-issue endpoints.
[CIRCULATION.md](CIRCULATION.md) specifies their bodies, receipt, limits and errors.
PHASE 8 adds direct issue, return/lost, exact inventory lookup, overdue, Reader
selection, and owned active/history borrowing endpoints, also documented there.

PHASE 5 standard/fuzzy search, autocomplete, search click attribution and
single-reference lookup endpoints are implemented. See [SEARCH.md](SEARCH.md)
for exact filters, pagination, ranking, ownership and event semantics. Semantic
and Hybrid endpoints are implemented as documented in SEMANTIC_SEARCH.md.

PHASE 4 catalog, reference, copy, cover and Reader-view endpoints are now
implemented and exported. [CATALOG.md](CATALOG.md) records methods, permissions,
pagination, DTOs, lifecycle and upload rules. The remaining implemented groups
are listed below with their phase-specific contract documents.

| Method/path | Actual behavior |
|---|---|
| GET /health and /api/v1/health | Backend process liveness, 200 with status ok; independent of database, Redis and LLM availability |
| GET /ready and /api/v1/ready | Actual SELECT 1 and Redis PING; 200 ready or 503 unavailable with safe dependency status |
| GET /docs and /openapi.json | Development/test Swagger and OpenAPI; disabled when APP_ENV=production |

Through Nginx, /health belongs to Next.js; use /api/v1/health for backend liveness. Internal container probes use the backend's unprefixed routes. Readiness responses use Cache-Control: no-store. API request logs and responses carry a generated X-Request-ID.

Export from the project root with `backend/.venv/Scripts/python.exe scripts/export_openapi.py`; then run `npm run api:generate` in frontend. Commit both docs/openapi.json and frontend/types/api.generated.ts. `scripts/verify_phase1.ps1` checks schema and generated-type drift. It does not require a live database for contract export.

The central client implements same-origin /api/v1 requests, cancellation, JSON/204 handling, safe standard errors, in-memory access credentials, serialized refresh, CSRF headers and logout propagation. Authenticated PDF/XLSX downloads use the same client and refresh policy.

## Implemented authentication endpoints

All paths below have the `/api/v1/auth` prefix. Responses use no-store. Request
schemas reject unknown fields. [AUTHENTICATION.md](AUTHENTICATION.md) defines
password policy, cookies, CSRF, rate limits, session revocation and permissions.

| Method/path | Authentication and result |
|---|---|
| GET /csrf | Returns a cookie-bound CSRF proof; rejects unapproved supplied origins |
| POST /register | CSRF + allowed Origin; 201 safe UserResponse; always ACTIVE/READER |
| POST /login | CSRF + allowed Origin; access token/user JSON and HttpOnly refresh cookie |
| POST /refresh | CSRF + allowed Origin + refresh cookie; consumes credential and rotates it |
| POST /logout | CSRF + allowed Origin; revokes cookie session family and clears cookie; 204 |
| GET /me | Bearer token + live account/session; safe current UserResponse |
| POST /change-password | Bearer + CSRF + allowed Origin + current password; revokes all sessions; 204 |
| GET /sessions | Bearer; caller's active root sessions, safe timestamps/current marker |
| DELETE /sessions/{session_id} | Bearer + CSRF + allowed Origin; owned root only, 404 for another owner; 204 |

RegisterInput accepts email, first_name, last_name, password and optional phone.
Role/status/hash/session fields are excluded. LoginInput accepts email/password.
AuthResponse contains access_token, token_type, expires_in and user. Refresh
secrets only travel in Set-Cookie. UserResponse is an explicit allowlist, not an
ORM dump. GET /me reads current database status/role on every request.

Auth errors include 401 INVALID_CREDENTIALS/TOKEN_EXPIRED/TOKEN_INVALID/
UNAUTHORIZED/REFRESH_TOKEN_INVALID; 403 USER_BLOCKED/ACCOUNT_INACTIVE/FORBIDDEN/
CSRF_FAILED; 404 SESSION_NOT_FOUND; 409 EMAIL_ALREADY_EXISTS; 422 VALIDATION_ERROR/
PASSWORD_UNCHANGED; 429 RATE_LIMIT_EXCEEDED with Retry-After; and
503 AUTH_SERVICE_UNAVAILABLE when Redis cannot enforce a limit. Responses omit
passwords, submitted tokens, SQL and internal exception details.

## Contract conventions

REST under /api/v1. UUID identifiers; ISO 8601 timezone-aware timestamps; stable enum values. Pagination uses items, page, page_size, total, pages with bounded page_size. Sorting uses backend allowlists. Search supports q/category/author/publisher/language/year_from/year_to/available/sort/page/page_size and typed semantic/hybrid filters.

Central exceptions return `{ "error": { "code": "...", "message": "safe localized text", "details": null } }`. Preserve all PART 40 error codes. INTERNAL_ERROR is confirmed by that part's explicit production example despite its earlier broken line wrap. Use 401 authentication, 403 permission, 404 unavailable/not-visible resource, 409 state conflict, 422 validation, 429 rate limit and 503 unavailable subsystem. Ownership denials use 404 on object lookups to limit enumeration; role denial uses 403.

OpenAPI/Pydantic schemas drive generated or checked TypeScript types. Any contract edit updates schemas, routes, service, client, affected UI, tests and docs together. A centralized frontend client handles refresh, cancellation, errors and authenticated file downloads.

## Endpoint groups and authority

| Group | Required scope |
|---|---|
| auth | register/login/refresh/logout/me/password/session endpoints implemented above; profile editing is implemented under users/me |
| books/authors/categories/publishers/copies | public catalog reads and authorized metadata/copy mutations |
| search | standard, semantic, hybrid and bounded autocomplete |
| reservations | create, own list, owned detail, cancel; authenticated own READY QR retrieval |
| librarian/qr | verify opaque token; separately authorized manual reservation-number lookup with same eligibility rules |
| librarian/reservations/{id}/issue | explicit reserved issue; verification never calls this automatically |
| librarian/borrowings | direct issue, inventory lookup, return and overdue; validated lost/damaged workflows |
| borrowings/me | active/history; no reader return mutation |
| favorites, notifications | owned list and mutation endpoints |
| recommendations, books/{id}/similar, books/popular | real catalog results and current availability |
| ai | owned conversations/messages; categorization requests and human review |
| admin | users/librarians, roles/status, settings, audit, six analytics groups and report generation/download |

The manual-number lookup is an additional contract required by PARTS 7/97/115; reservation numbers are public identifiers, never QR secrets. It returns a preview only and remains librarian-authorized/rate-limited/audited.

## Cross-cutting response design

Book responses aggregate total_copies/available_copies and appropriate shelf summaries. Assistant book IDs are validated backend results. Reports expose validated state and authorized download responses. Do not expose password hashes, raw refresh credentials, QR secrets in ordinary lists, internal paths or provider keys.

Actor identity comes from authenticated context. Public registration has no privileged role assignment. Role and object checks remain mandatory behind every UI and AI tool. Feature documents record actual methods, schemas and status codes; the generated endpoint inventory and OpenAPI are the executable contract.

## PHASE 14 categorization

POST /api/v1/ai/categorize; GET /api/v1/ai/category-predictions and /{id};
POST /{id}/review. Staff-only generation and explicit final-category confirmation.
See CATEGORIZATION.md and generated OpenAPI for fields, safe errors and limits.

## PHASE 15 owned assistant

POST/GET /api/v1/ai/conversations; GET /{id}; POST /{id}/messages. Reader-only,
owned, paginated history and request_id idempotence. Message output contains
validated real book cards. No client-selected user, arbitrary tools or raw provider
metadata. AI_SERVICE_UNAVAILABLE preserves other services. See AI_ASSISTANT.md.

## PHASE 16 analytics

GET /api/v1/admin/analytics/{overview,circulation,inventory,readers,search,ai}.
ADMIN only. Optional inclusive date_from/date_to; maximum 3660 days.
OpenAPI/generated TypeScript define responses; ANALYTICS.md defines metrics.


## PHASE 17 reports

POST /api/v1/admin/reports accepts report_type, format, date_from/date_to; returns
PDF/XLSX attachment. ADMIN/Origin required; 6 per minute, 5000-row explicit limit.
See REPORTS.md and generated OpenAPI for contract and metric semantics.


PHASE 19: cover upload is limited to 30 per account/minute (429/503 documented).
All requests bearing Authorization receive no-store, including catalog reads.
