# PHASE 19 security review

Reviewed the implemented auth/session, authorization, storage, circulation, AI,
analytics/report, worker and proxy boundaries against PARTS 41–57, 160–168 and 191.
This is a code/test review, not an independent penetration test.

| Boundary | Result / evidence |
|---|---|
| Password/session | Argon2id, minimal signed claims, current database role/status, hashed rotating refresh families, replay revocation and CSRF preserved; test_auth and test_auth_security |
| RBAC/ownership | Explicit role capabilities, private owner predicates, live write rechecks; cross-surface role matrix and existing Admin/Reader/assistant/QR tests |
| Catalog caching | Fixed: all Authorization-bearing responses use no-store, including inventory and archived catalog reads |
| Production QR configuration | Fixed: validate actual Fernet key at startup, in addition to independent non-default auth/QR credentials |
| Uploads | Generated names, approved MIME plus decoded/re-encoded content, size/pixel bounds, non-executable storage; added 30/account/minute cover limit before decoding |
| Browser XSS | Added per-request script nonce CSP, no production unsafe-inline/eval scripts, no frames/objects, same-origin connections and camera-only permission; actual HTML injection blocked in Edge |
| SQL/transactions | Parameterized ORM, sort allowlists, restricted database role, immutable audit, shared lock order and PostgreSQL uniqueness/owner constraints retained |
| AI | Pinned safetensors/no remote code; validated JSON categorization artifacts; nine read-only tools, identity from principal, provider HTTPS allowlist, bounded context/time/response, no raw factual model prose |
| Reports/audit/logs | Explicit safe projections, binary private attachments, escaped PDF, typed formula-safe XLSX, audit reason allowlist, no request/secret payload logging |
| Jobs | Shared locks, per-item transactions, late acknowledgement, bounded retries, durable event uniqueness and actual restart test |
| Secrets/network | .env/caches/venvs ignored; no host PG/Redis ports; application runtime role only; TLS/HSTS configuration and final deployment verification belong to PHASE 21 |

Nonce HTML is dynamically rendered and cannot be shared cached. Static assets keep
their ordinary cache behavior. Inline styles remain allowed for Recharts/popovers;
React escapes catalog/profile content and no arbitrary HTML renderer exists.
Development alone allows eval/WebSocket debugging; production scripts do not.
Nginx HTTP remains a local development entry point pending PHASE 21 TLS setup.

Actual checks: 66 PostgreSQL/Redis security/auth/catalog/Admin tests, 98 native,
69 frontend, production frontend build and five Edge security/auth flows passed.
The parser-injection test uses altered test HTML while retaining real CSP headers;
DevTools execution is not treated as untrusted HTML. Production npm audit reported
zero known vulnerabilities on 2026-09-27; this does not prove absence of vulnerabilities.
No real secrets appeared in the audit result. No migrations were changed.

References: [Next.js nonce CSP](https://nextjs.org/docs/app/guides/content-security-policy),
[OWASP CSP](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html),
[OWASP uploads](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
