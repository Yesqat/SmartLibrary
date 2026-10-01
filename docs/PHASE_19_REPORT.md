# PHASE 19 — Security hardening

Status: **PHASE 19 COMPLETE — PROCEEDING TO PHASE 20**. Verified 2026-09-27.

1. **Implemented:** cross-system security review; startup Fernet validation,
   authenticated response cache protection, cover rate limiting, nonce script CSP
   and browser permissions. See SECURITY_REVIEW.md for boundaries and limitations.
2. **Created:** frontend/proxy.ts, lib/security-policy.ts and its tests;
   native/database test_hardening.py; tests/e2e/security.spec.ts; review/report.
3. **Modified:** config/main/catalog, foundation config test, root layout, dev
   proxy mount, OpenAPI/types and affected documentation. Working auth retained.
4. **Migrations:** none. Isolated chain through 0005 round-trip/head/drift passed.
5. **API:** upload 429/503 documented; no new route. Authenticated catalog no-store.
6. **Frontend:** every HTML response gets a fresh nonce; pages now render on demand.
   No production inline-script/eval allowance; inline styles support chart layout.
7. **Tests:** five native, six database (including four-role matrix), two frontend
   policy cases and real browser CSP enforcement; preserved all valid assertions.
8. **Executed:** Ruff lint/format, mypy, native pytest, actual database-tests,
   OpenAPI export/check/types, ESLint/Prettier/types/Vitest/build, frontend restart,
   Edge auth/security, npm audit --omit=dev, git check-ignore and spec hash.
9. **Results:** PostgreSQL/Redis **66 passed**, zero skips, 31.20 s; native **98
   passed**, 5.57 s; Ruff **188 files**, mypy **149 sources**. Frontend **69 passed**,
   10.54 s; build/lint/format/type passed. Browser **5 passed**, 41.4 s. Npm production
   audit **zero known vulnerabilities**. Logs: work/logs/phase19-*.
10. **Fixed:** listed review gaps; test borrowing route corrected to actual
    /me/active and /me/history. First browser run omitted staff test credentials,
    hit a cold navigation timeout and tested DevTools trust rather than parser
    injection; corrected test setup, retained auth assertions, final run passed.
    Ruff cache ACL avoided with --no-cache. No security controls weakened.
11. **External:** public TLS/domain remains PHASE 21 deployment configuration;
    actual external LLM success remains credential-dependent as documented.
12. **Inherited:** unchanged domain/AI ownership and concurrency evidence from
    owning phases; PHASE 20/22 consolidate those suites. PHASE 18 worker restart
    evidence unchanged. Runtime images are rebuilt in PHASE 21.
13. **Specification:** unchanged SHA256
    DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.
14. **Next:** PHASE 20 completes the coverage matrix and integrated E2E regression.
