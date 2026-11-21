# Production-like deployment

Use the base Compose file plus docker-compose.production.yml. Never combine the
production and development overrides. Compose 2.24.4+ supports the port/volume
replacement syntax; current verification uses Compose 5.5.1. Runtime images have
no source mounts, no development accounts and no browser-visible secrets.

## Configuration and first startup

1. Provide a DNS name and its valid TLS certificate. Keep fullchain.pem (server
   then intermediates) and privkey.pem in an access-restricted workspace directory
   such as var/tls. Only Nginx mounts it, read-only. Renew externally, then run
   `nginx -t` and `nginx -s reload` in that service. Do not use the local test CA
   for public deployment.
2. Run `python scripts/init_production_env.py --host library.example.org` with
   the actual hostname. It creates .env.production once, with independent random
   database/Redis/JWT/QR secrets and no development seed password. Existing files
   are preserved. Configure the actual library timezone and optional LLM settings
   privately. Keep QR encryption keys across recovery or existing QR ciphertext
   cannot be decrypted. Never reuse development credentials.
3. Loopback is the safe default. For an intended public deployment explicitly set
   DEPLOY_BIND_ADDRESS to the host's ingress address (or 0.0.0.0 after reviewing
   firewall rules), HTTP_PORT=80 and HTTPS_PORT=443. PUBLIC_ORIGIN must be the exact
   HTTPS browser origin; PUBLIC_HOST is the certificate hostname without a port.
4. Use a separate Compose project for production. Do not accidentally attach
   production to development volumes.

```powershell
$production = @('compose','-p','smartlibrary-production','--env-file','.env.production','-f','docker-compose.yml','-f','docker-compose.production.yml')
docker @production config --quiet
docker @production build backend frontend
docker @production up -d --wait postgres redis
docker @production run --rm database python -m app.db.manage upgrade
docker @production run --rm database python -m app.db.manage check
docker @production run --rm database python -m app.db.bootstrap_admin
docker @production up -d --wait --wait-timeout 180
```

The interactive initial-Admin command validates the normal password/account
policy, uses Argon2id, creates ACTIVE ADMIN and records an audit event. It never
promotes an existing account and refuses if any Admin exists. Concurrent attempts
serialize on the same Admin membership lock. Later staff creation uses public
READER registration followed by authenticated Admin role management. Development
seed refuses production; never enable it to obtain a first Admin.

Install/download the pinned embedding model and reviewed categorization artifact
using SEMANTIC_SEARCH.md and CATEGORIZATION.md. Missing AI artifacts/provider
credentials do not prevent catalog/circulation readiness. Then generate the real
catalog index. Optional AI provider settings are documented in the
[assistant setup guide](AI_ASSISTANT.md#configuration-and-unavailable-behavior).

## Ingress and runtime behavior

Only Nginx publishes HTTP/HTTPS. HTTP redirects with 308 to the configured HTTPS
origin, preserving the path/query; the plain liveness probe is an exception.
TLS 1.2/1.3, HSTS, canonical Host validation, 10 MiB request ceiling and safe
413 JSON are configured. A 75-second upstream timeout accommodates the bounded
60-second assistant deadline. Host/protocol/client-address headers are overwritten
at ingress; backend trusts only this private topology. Never publish backend ports
with TRUST_PROXY_HEADERS enabled. There is no trusted upstream load balancer by
default; review exact proxy addresses if introducing one.

Frontend nonce CSP is preserved by Nginx. Production disallows eval and uses
private no-store dynamic HTML. CORS is limited to PUBLIC_ORIGIN; refresh/CSRF
cookies are Secure/HttpOnly with __Secure-/__Host- names and strict SameSite.
Swagger/OpenAPI HTTP endpoints are disabled. Backend errors remain safe JSON.
PostgreSQL/Redis remain on the internal network, with no published host ports.
Application processes run as non-root. Restart policies and bounded Docker logs
(three 10 MiB files/service) support operational recovery.

Eight services have actual health checks: frontend, backend, PostgreSQL, Redis,
worker, ml-worker, beat and Nginx. Readiness queries PostgreSQL and Redis with
timeouts; liveness does not depend on LLM/network credentials. One Beat instance
is intended; duplicate job delivery is safe through transactional deduplication.

## Local HTTPS verification

The verification project is **smartlibrary-production-check**, with independent
database/Redis/uploads and secrets, ports 8082/8443, APP_ENV=production. Generate
short-lived localhost files using `python scripts/create_local_tls.py`; this does
not install certificates or change OS trust. Configure .env.production with
`init_production_env.py --host localhost --http-port 8082 --https-port 8443
--tls-directory var/tls-verification` on an environment without that file.

`python scripts/verify_production.py` verifies the local CA chain and hostname,
redirects, HSTS/CSP, restricted origins, Secure cookies, request size, private
services, live schema and health. `playwright.production.config.ts` verifies real
registration/login/refresh/logout over TLS. Its local test browser context accepts
the private CA; Python separately requires full certificate verification.

On this Windows host Kaspersky intercepted the private CA and returned its own
499 warning page. No antivirus or OS trust setting was changed. The same browser
test can run inside the pinned matching Playwright container on the application
network: `python scripts/run_tls_browser.py`. It mounts only frontend/test/script
sources read-only and a dedicated result directory; private .env files are not
mounted. The JavaScript helper forwards TCP only, keeping TLS between Chromium
and Nginx. See PHASE_21_REPORT.md for actual results.

Public DNS, publicly trusted TLS and external LLM inference require real operator
configuration. Local verification does not claim public deployment or provider
quality. See BACKUP_RECOVERY.md before operating with real Reader data.

References: [Nginx HTTPS](https://nginx.org/en/docs/http/configuring_https_servers.html),
[Compose merge rules](https://docs.docker.com/reference/compose-file/merge/),
[Playwright Docker](https://playwright.dev/docs/docker).
