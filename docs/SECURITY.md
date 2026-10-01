# Security design

PHASE 13 recommendation receipts use a purpose-derived HMAC key, bind authenticated
Reader/session family and actual returned IDs, and expire after 30 minutes. They
are not access tokens. Event writes recheck live session and ownership, require
allowed Origin, and use rate limits and database deduplication. Recommendations
never expose raw profiles/vectors or allow request-selected personal identities.

PHASE 12 models use reviewed immutable revisions, safetensors, local-only runtime
loading and no remote model code. Downloads are explicit operator actions with TLS
verification. Vector requests have an additional Redis IP limit; filters, event
ownership and catalog RBAC remain enforced. Background inference rechecks metadata
under locks before publishing. Dedicated ML queue bounds inference concurrency;
model outages leave standard search and circulation operational.

PHASE 11 Admin writes enforce live ADMIN permission, Origin, rate limits and
transactional audit. Role/status changes revoke all target sessions and preserve
the last ACTIVE ADMIN under concurrent changes. Settings use strict database
types/bounds and optimistic versions. Audit API is read-only and projects only
safe reasons, never raw audit JSON or auth material. See ADMIN.md.

Status: authentication, RBAC/ownership foundations, CSRF, Redis auth limits and
transactional audits are preserved. PHASE 4 adds catalog authorization and cover
upload validation. PHASES 6–7 add private encrypted QR credentials and separate
Librarian verification/issue. Controlled AI boundaries are implemented. See
AUTHENTICATION.md, CATALOG.md and phase reports. No penetration-test claim.
Sources: PARTS 5–8, 41–57, 163–168, 176, 181–182 and 191.

## Implemented foundations

PHASE 9 Reader/profile ownership and validated avatar lifecycle are documented
in READER.md. Email is read-only; profile input cannot assign privileges/history.
PHASE 10 manual reservation lookup is Librarian-only, rate limited and audited;
it shares QR state validation and never issues. Camera video stays in the browser.
Operational Reader views exclude authentication secrets and AI conversations.

PHASE 8 direct issue/return/lost share the book and sorted-user transaction locks.
Durable scoped retry UUIDs deduplicate direct issue; terminal return/lost repeats
cannot mutate later circulation. Negative Reader/Admin mutation and ownership
tests run against PostgreSQL. Reader GET borrowing routes are owner-scoped;
staff selection exposes only bounded safe account fields. See CIRCULATION.md.

Reservation mutations recheck session/role under database locks; owner routes
hide other users' records. QR uses 256 random bits, SHA-256 lookup, Fernet at rest,
READY/expiry/copy checks and no-store responses. Redis limits fail closed. See
[RESERVATIONS.md](RESERVATIONS.md). Browser tests disable credential-bearing traces.

PHASE 4 also implements bearer-only, Origin-checked catalog writes, transactional
live-role rechecks, safe archive restrictions and decoded/re-encoded cover
uploads. See [CATALOG.md](CATALOG.md) for image limits, generated paths and orphan
cleanup. Cookie-based authentication endpoints keep their existing CSRF proof.

Typed Pydantic settings require non-default PostgreSQL/Redis passwords, explicit origins/hosts, valid timezone and bounded token lifetimes. JWT_SECRET is required with at least 32 non-default characters in every environment. Production configuration rejects HTTP browser origins, short/default QR secrets, identical auth/QR secrets and DEBUG logging; Swagger is disabled.

Application images run as non-root with no-new-privileges. PostgreSQL and Redis have no host mappings and share an internal data network. Only Nginx publishes a loopback port. Redis requires a password. PHASE 2 supplies an explicit operator command to provision non-superuser migration and runtime roles. API/worker environments contain only runtime database credentials; the opt-in operator/test services receive privileged credentials. Apply the documented role bootstrap and migrations before restarting API/worker. Live grants and denial of runtime DDL, history deletion and audit mutation were verified against PostgreSQL.

The environment helper creates independent random development credentials without overwriting an existing .env or printing values. Git/Docker ignore rules exclude secrets, caches and build artifacts. FastAPI uses explicit CORS/TrustedHost settings and safe exception responses; request logs omit bodies, authorization headers, raw URLs and query strings. Nginx sets nosniff/referrer/frame headers and a 10 MiB request cap. Nonce script CSP is implemented; production TLS/HSTS use the separate production override. The local HTTP configuration remains loopback-only.

## Authentication and authorization

Implemented: Argon2id password hashes; short-lived access JWTs with minimal claims; opaque rotated refresh tokens with only hashes persisted. Browser access tokens stay in memory; refresh credentials use HttpOnly cookies, Secure in production, SameSite=Strict and /api/v1/auth scope. All auth mutations enforce a cookie-bound CSRF proof and an allowed Origin. Password/session mutations also require a bearer token. No credentials are stored in localStorage/sessionStorage. See AUTHENTICATION.md for exact parameters and absolute family expiry.

Validate token signature/expiry and current account status/role for protected requests. Public registration always creates READER. Logout revokes the session; refresh reuse revokes its token family. Password change verifies current password and revokes existing refresh sessions under the documented policy. Role/status changes invalidate affected authorization promptly; stale token claims cannot retain privileges.

Exactly READER, LIBRARIAN and ADMIN. No AI role or implicit admin bypass. Staff operational permissions must be explicit; the current operational plan requires LIBRARIAN for issue/return/QR. ADMIN manages users/configuration/analytics and catalog as specified. Any expansion of admin circulation permissions needs an explicit permission decision before implementation.

Owned-session operations enforce caller identity with 404 for another owner's session. Reservations, loans, favorites, notifications, recommendations and conversations enforce ownership. Profile mutation schemas exclude role, status and history. Email remains read-only in the initial profile contract; secure email change and email password reset are optional extensions, never misleading nonfunctional flows.

## QR and manual fallback

Owner QR and Librarian verification/issue are implemented and tested; see
[RESERVATIONS.md](RESERVATIONS.md) and [CIRCULATION.md](CIRCULATION.md). The latter
requires a short-lived, purpose-separated receipt plus current Librarian session
and all live eligibility checks. Camera/manual-number fallback is implemented in PHASE 10.

Use cryptographically random opaque tokens. PHASE 2 stores a hash, encrypted recoverable token and key identifier, with READY-only credential lifecycle checks and deferred ORM loading of sensitive fields. The development fixture uses real random token generation and Fernet encryption. Owner-authorized QR endpoints use this storage without exposing it in ordinary lists. Encryption keys are environment-managed and separate from JWT secrets; document rotation when implemented. The owner-only QR response must use no-store and return credentials only for valid READY state.

Invalidate/erase recoverable token material when reservation completes/cancels/expires. Verify READY, expires_at > now, ACTIVE user and matching RESERVED copy. Issue revalidates under locks; possession or previous verification never authorizes issue alone. Manual reservation-number lookup is librarian-only and uses the same safe preview/eligibility checks; numbers are not secrets. Rate-limit and audit both paths, without recording raw tokens. A scan never issues a book.

## Boundary controls

PHASE 2 database defenses include composite owner/reference foreign keys, hashed
refresh-token family lineage, restricted runtime deletion, audit mutation and
TRUNCATE guards, immutable embedding-model provenance and typed/range-checked
settings. These do not authorize HTTP requests or sanitize JSON payloads.
Explicit public schemas and safe logs omit password/session/QR secrets.
The API exposes documented catalog, circulation, Reader, Admin, AI and reporting routes.
Auth rate limiting fails closed with 503 on Redis failure. Nginx overwrites
client-address headers; trusting those headers is explicit and safe only when
backend ingress is restricted to that proxy. Security audits and application
logs use allowlisted fields; unexpected errors record type, SQLSTATE and code
locations without exception strings or SQL parameters.

- Central Pydantic validation and domain rules; SQLAlchemy parameterized queries, explicit safe sort allowlists and bounded pagination.
- Redis-backed rate limiting for auth, semantic/hybrid search, AI and QR. Define safe dependency-failure behavior for security-sensitive paths; do not silently disable limits in production.
- React escaping, controlled rich content, CSP, content-type protections, referrer policy and production HSTS/HTTPS. Narrow configured CORS; no wildcard authenticated production origins.
- Covers/avatars: authenticated authorization, size limits, approved JPEG/PNG/WEBP types, decoded image inspection and safe generated names. Store outside executable code; safe URL responses and orphan cleanup through storage service.
- Typed environment validation; reject insecure production defaults. .env.example contains safe examples only, real secrets ignored. Never log authentication headers, passwords, raw tokens or keys.
- AI tools use authenticated services and minimal data; prompt injection cannot bypass authorization. LLM has no SQL tool or database credentials.
- Structured application logs carry request ID, safe route/status/duration and failures. Transactional audit covers significant security/domain changes; ordinary UI cannot edit/delete audit records.
- PostgreSQL/Redis remain private; least-privilege runtime database access and controlled migration credentials. Reports and downloads require authorization and omit secrets.

## Environment distinction

Development can use localhost and local image storage with explicit development accounts once seeded. Production requires HTTPS, secure cookies, non-default secrets, restricted origins and safe errors. No working reset-email claim without actual configured email delivery. Verify these controls incrementally and repeat threat review in PHASE 19 and Final Verification.

## PHASE 14 review boundary

Categorization is staff-only and cannot assign categories automatically. Review
locks and rechecks live authorization, book content, assigned categories and
taxonomy; only existing active IDs are accepted. Artifacts are bounded validated
JSON, never executable pickle. External provider access is not involved.

## PHASE 15 AI boundary

Nine allowlisted read-only tools revalidate the live Reader/session and reject
extra arguments. The model cannot select another user or write circulation data.
Final output is a validated evidence/reference plan; backend facts are rendered
without arbitrary model factual prose. Provider HTTPS destination is fixed; no
redirects, raw payload logging or secret tool fields. Redis rates, bounded context,
short transactions and mid-flight revocation checks are verified. See AI_ASSISTANT.md.

## PHASE 16 analytics

Admin analytics use VIEW_ANALYTICS, no-store and 60/account/minute limiting.
Read-only repeatable-read snapshots have a 10-second statement timeout.
Aggregated responses omit identity secrets and assistant message content.


## PHASE 17 report security

Reports are ADMIN-only, no-store, rate/row/time bounded and use explicit safe columns.
Live authorization is rechecked after rendering; safe generation metadata is audited.
PDF text is escaped; XLSX strings cannot become formulas; no public report files.


PHASE 19 cross-system review and verified hardening: see SECURITY_REVIEW.md.

PHASE 21 adds production TLS 1.2/1.3, HSTS, canonical Host/redirect validation,
bounded logs and safe Nginx upload-limit errors. The operator-only initial Admin
command refuses an existing Admin or account and audits creation; public
registration remains READER-only. Production runtime cookies and nonce hydration
were tested in an isolated HTTPS environment. See PRODUCTION_DEPLOYMENT.md.


Final cross-system execution and review are in FINAL_REVIEWS.md and
FINAL_ACCEPTANCE_MATRIX.md. The complete PostgreSQL/Redis suite, negative role/
ownership cases, real CSP and production TLS/session checks ran in PHASE 22.
