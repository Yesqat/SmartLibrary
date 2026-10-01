# Authentication and authorization

Implemented in PHASE 3. This document describes the real auth contract; catalog,
circulation, profile editing, administrative role/status changes and AI tools
remain in their assigned phases. See [PHASE 3 report](PHASE_3_REPORT.md) for
executed verification and [Master Specification](../MASTER_SPECIFICATION.md)
PARTS 5–8, 28, 30, 40–57, 163–166, 183 and 189–194 for authority.

## Credentials and account lifecycle

Registration accepts only first/last name, email, password and optional phone.
It always inserts ACTIVE/READER. Extra fields, including role, status, IDs and
password_hash, fail validation. Email is validated and normalized to lowercase;
duplicate registration returns 409 EMAIL_ALREADY_EXISTS. Login gives the same
401 INVALID_CREDENTIALS for an unknown email and a wrong password. A dummy
Argon2 verification is performed for unknown accounts. BLOCKED/INACTIVE errors
are returned only after a correct password, or for an authenticated request.

Passwords use Argon2id with 64 MiB memory, three iterations and parallelism four,
random salts, verification and rehash-on-login when parameters change. New
passwords require 12–128 characters, at most 512 UTF-8 bytes, no leading/trailing
whitespace/control characters, and reject common passwords or fewer than four
distinct characters. Unicode/passphrases are supported; there is no forced
punctuation/uppercase recipe. Phone numbers, when supplied, require 7–15 digits.

Password change verifies the current password under the user lock, rejects an
unchanged new password, hashes the replacement and revokes **all** session
families in the same transaction as its audit event. The browser returns to
login. Password reset by email and profile/email editing are not exposed here.

## Access and refresh

- Access JWTs use HS256 with a configured independent signing secret of at least
  32 characters. The verifier fixes the algorithm, issuer and audience and
  requires `sub`, `sid`, `type`, `iat`, `nbf` and `exp`. Claims contain no email,
  phone, password, hash or role. Role/status come from the current database row.
- Default access lifetime is 900 seconds. Tokens are kept only in browser memory,
  sent in Authorization: Bearer, and never persisted to local/session storage.
- Refresh credentials are 48 cryptographically random bytes encoded as URL-safe
  text. PostgreSQL stores only their SHA-256 hashes in the existing session model.
  The raw value is delivered only as an HttpOnly cookie, never response JSON.
- Each login creates a root session whose ID is its family ID. The access `sid`
  points to that root. The default absolute family lifetime is 30 days; rotation
  does not extend it. Each replacement records its predecessor and keeps that
  same expiry, reinforcing the existing lineage/uniqueness constraints.
- Rotation locks the user, reloads the credential after acquiring the lock,
  consumes it and inserts one successor atomically. Reuse of a consumed credential
  revokes the whole family, including access JWTs, and is audited. Lost refresh
  responses may require login again; replay is not silently accepted.
- Every protected request validates both JWT and current database user/root
  session. Logout, session revocation and password change therefore invalidate
  existing access immediately. A blocked/inactive account is denied and its
  families revoked when encountered. Future administrative status-change services
  must revoke sessions in their own transaction as well.

All auth responses, including errors, use Cache-Control: no-store. The access
response includes only access_token, token_type, expires_in and a safe user DTO.
Session lists expose root ID, creation/expiry time and whether it is current.

## Cookies and CSRF

Development uses `sl_refresh`; production uses `__Secure-sl_refresh`. Both are
HttpOnly, SameSite=Strict and scoped to `/api/v1/auth`. Production adds Secure;
no Domain is set. The pre-login binding cookie is `sl_csrf` in development and
`__Host-sl_csrf` in production, HttpOnly, SameSite=Strict, path `/`, one-hour
lifetime, Secure in production.

Before a mutation, fetch GET `/api/v1/auth/csrf`. It returns a signed proof bound
to the current refresh cookie, or a random pre-login cookie when no refresh
exists. Send the proof in X-CSRF-Token. Every auth mutation, including registration
and login, requires a configured exact Origin, rejects cross-site Fetch Metadata
and checks that proof in constant time. Rotation changes the binding, so clients
fetch a fresh proof before each mutation. GET csrf rejects an explicitly untrusted
Origin. This is a same-origin browser architecture behind Nginx; credentials are
not transported in URLs, hidden form fields or browser storage.

The client shares one refresh promise per tab and uses Web Locks across tabs to
serialize cookie operations. BroadcastChannel propagates logout. Older browsers
without Web Locks retain safe server replay rejection but may need to log in
again after simultaneous refresh attempts. Late responses cannot restore local
identity after logout. Account/role/status changes clear cached queries.

## Rate limits and trusted ingress

Atomic Redis INCR/EXPIRE windows enforce these defaults:

| Operation | Default limit |
|---|---|
| Login | 30/IP and 10/normalized account per 900 seconds |
| Register | 10/IP per hour |
| Refresh | 120/IP per minute |
| CSRF proof | 240/IP per minute |
| Password change | 10/IP per 900 seconds |
| Logout/session revocation | 120/IP per minute |

Login/register/refresh settings are environment-configurable. Redis keys use
domain-separated HMAC identifiers instead of plaintext IPs/emails. Exceeding a
limit returns 429 RATE_LIMIT_EXCEEDED and Retry-After. Redis failure returns safe
503 AUTH_SERVICE_UNAVAILABLE; limits are never silently bypassed. Reading an
already authenticated account depends on PostgreSQL, not the rate-limit service.

Native backend runs ignore forwarding headers by default. Compose explicitly
enables TRUST_PROXY_HEADERS because the backend has no published port and Nginx
is the trusted ingress. Nginx overwrites X-Real-IP and X-Forwarded-For with its
actual peer address. If deployment adds a load balancer or exposes the backend,
review this trust boundary before enabling the flag; never trust arbitrary
internet-supplied forwarding headers. PostgreSQL and Redis remain private.

## Permissions and ownership

`current_principal` validates active identity/session. `require_permission`
wraps it with the explicit capability map in `core/permissions.py`:

| Role | Capabilities prepared for owning feature phases |
|---|---|
| READER | Own reader data, reserve |
| LIBRARIAN | Catalog management, circulation/QR, relevant reader operations |
| ADMIN | Catalog, users/roles, settings, analytics/reports, audit |

There is no blanket ADMIN bypass for circulation or ownership. Account/security
operations are available to all active roles for their own identity. The reusable
`authorize_owner` helper returns 404 for another owner's object. Session listing
is filtered by authenticated ID, and session deletion rechecks ownership in its
transaction. Bodies never select the acting user. Future reader/AI services must
use the same principal and ownership checks; their routes are not introduced as
test stubs in production.

Frontend `/dashboard`, `/librarian`, `/admin` and `/account/security` use protected
layouts. Public HTML contains no private user data; the browser obtains it through
the authenticated backend. Guards provide loading/error/denial/redirect behavior.
Their role landing pages currently show real account data and security actions;
circulation dashboards, administrative management and analytics remain later work.

## Audit, failures and configuration

Transactional events include USER_REGISTERED, LOGIN_SUCCEEDED, LOGIN_FAILED,
LOGOUT, PASSWORD_CHANGED, PASSWORD_CHANGE_FAILED, SESSION_REVOKED and
REFRESH_REUSE_DETECTED. They contain actor/entity IDs, a controlled reason where
needed, normalized IP and request correlation ID. Passwords, token values/hashes,
submitted emails and full request bodies are never written to audit details.
No-detail events use an empty JSON object, matching the schema's object constraint.

Clients receive centralized safe Kazakh errors with stable codes. Validation
does not echo submitted values. Server exception diagnostics retain type, SQLSTATE
and function/line metadata without exception messages, SQL parameters, headers
or stack local variables. Existing immutable audit triggers remain unchanged.

Use the private `.env` created by the existing initializer. `JWT_SECRET` is now
required in every environment. Keep it distinct from QR and database credentials.
No new secret or schema migration is required for this phase. Existing seeded
accounts use the private DEV_SEED_PASSWORD; public registration cannot create
privileged accounts. Production still requires the HTTPS deployment of PHASE 21.

References used for the library/security implementation: [PyJWT validation](https://pyjwt.readthedocs.io/en/stable/usage.html),
[Argon2 parameters and rehashing](https://argon2-cffi.readthedocs.io/en/stable/api.html),
[OWASP CSRF controls](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).


## Password reset boundary (PART 165)

Password hashing, session revocation, rate limiting and transaction services are
reusable for a future reset-token service. SMTP/email reset is not configured;
no misleading working Forgot Password flow is exposed. A future implementation
must add hashed single-use expiring tokens and delivery before exposing that flow.
Profile editing is implemented separately in READER.md.
