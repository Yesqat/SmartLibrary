# PHASE 15 — Grounded AI Librarian Assistant

Status: **PHASE 15 COMPLETE — PROCEEDING TO PHASE 16**. Verified 2026-09-27.

## 1. Implemented

Provider abstraction, real OpenAI Responses adapter, nine controlled read-only
backend tools, bounded multilingual conversation context, owned durable history,
validated evidence/book references, safe failures and Reader interface.
Factual prose comes from backend evidence; model-generated arbitrary library facts
cannot enter the final presentation. See AI_ASSISTANT.md for exact behavior/limits.

## 2. Files created

backend/app/ai/assistant/{__init__,contracts,policy,provider,tools,orchestration,service}.py;
schemas/assistant.py; api/v1/routes/assistant.py; tests/test_assistant_provider.py;
tests/database/domain/test_assistant.py. Frontend features/assistant/{api,chat,
messages,page}, locales/assistant.ts, app/(reader)/assistant/page.tsx,
tests/assistant.test.tsx; tests/e2e/assistant.spec.ts; docs/AI_ASSISTANT.md and this report.

## 3. Files modified

Backend router registration, pyproject/uv.lock (existing httpx promoted to explicit
runtime dependency), recommendation test setup isolation. OpenAPI/generated TS,
central API errors, Reader navigation, .env.example comments and affected README/
AI/API/security/database/UI/deployment/testing/plan/coverage documentation.

## 4. Migrations

None. Existing conversation/message/message-book tables and UUID keys suffice.
Isolated fresh migration round-trip/head/drift passed. No persistent data reset.

## 5. APIs

POST/GET /api/v1/ai/conversations; GET /{id}; POST /{id}/messages.
Reader-only, owned, no-store, bounded pagination/content, Origin/rate protection,
request UUID idempotence, concurrent-turn rejection and live authorization rechecks.

## 6. Frontend

/assistant with persisted conversation list/history, starter prompts, pending/error/
retry behavior, timestamps, escaped text and current real book cards. Card links
lead to the existing explicit reservation action; no AI mutation capability exists.

## 7. Tests added

Seventeen PostgreSQL/Redis cases cover real search/availability, real E5 semantic/
similar/personal tools, own loans/reservations/settings, arbitrary-user/SQL/write
rejection, ownership/RBAC, current-setting changes, idempotence, concurrent turns,
mid-flight blocking, interrupted recovery, bounded history, failures and rate limits.
Ten native adapter tests mock only external HTTP. Three components and one browser flow.

## 8. Executed commands

```text
uv lock --offline; uv sync --offline --group dev
ruff format <changed sources>; ruff check app [--fix]; ruff format --check app; mypy app
pytest -q app/tests/test_assistant_provider.py --basetemp=var/test-tmp
pytest -q --ignore=app/tests/database --basetemp=var/test-tmp
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -e PYTEST_ADDOPTS=<assistant targets> database-tests
docker compose run --rm -v C:/SmartLibrary/backend/app:/app/app -v C:/SmartLibrary/work/model-cache:/models:ro -e MODEL_CACHE_DIRECTORY=/models -e HF_HUB_OFFLINE=1 -e PYTEST_ADDOPTS=<assistant/reader/recommendations targets> database-tests
python scripts/export_openapi.py [--check]; npm run api:generate
npx prettier --write <changed frontend/E2E files>
npx vitest run tests/assistant.test.tsx
npm run lint; npm run format:check; npm run typecheck; npm test; npm run build
npx playwright test assistant.spec.ts --workers=1
python scripts/verify_stack.py --dev
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
Get-FileHash MASTER_SPECIFICATION.md -Algorithm SHA256
```

## 9. Actual results

- Initial assistant PostgreSQL **15 passed**, 11.11 s. Final affected gate
  **38 passed**, zero skips, 38.10 s; real E5 inference and Redis executed.
- Targeted fixture regression gates **2 passed** and **16 passed**.
- Ruff **166 files**, mypy **136 sources**, native **81 passed**, 7.53 s.
- Targeted components **3 passed**; full frontend **60 passed**. ESLint/Prettier/
  TypeScript and production frontend build **41 generated static pages** passed.
- Actual Edge flow **1 passed**, 7.6 s: provider unavailable, history persisted,
  catalog operational. No live external-model success is claimed.
- Eight development services healthy; current OpenAPI, routing, liveness/readiness,
  private PostgreSQL/Redis networking, worker/scheduler and both Compose checks passed.
- Logs: work/logs/phase15-{assistant-database,final-database,cold-start-isolation,
  attribution-isolation,browser,stack}.txt.

## 10. Problems fixed

Ruff formatting/types corrected. Combined tests revealed two older recommendation
fixtures assumed no earlier popularity: fixtures now establish an empty active
catalog in the disposable database and restore prior records, retaining assertions
and adding returned-book membership verification. Browser expected heading corrected
to the actual Kazakh label. No valid test removed, skipped or weakened.

## 11. External requirements

Configure private LLM_PROVIDER=openai, account-accessible LLM_MODEL and LLM_API_KEY
to exercise live external inference. Multilingual provider quality/account access
remain unverified. Internal tool/security/storage/failure boundaries are complete.
This does not block PHASE 16; no fake production AI fallback was introduced.

## 12. Inherited evidence

Unchanged core circulation/auth/security regressions inherit completed phases;
affected Reader/recommendation paths reran. Existing development/test images already
contain httpx; no new image build claimed. Current bind-mounted development stack
and native production frontend build verified. Final runtime images belong to PHASE 21/22.

## 13. Specification integrity

SHA-256 unchanged: DD0CD4F7248DFB4C900DD924FB0CCBAF73AC31F52F0945A2DC5179E288F48B61.

## 14. Readiness

PHASE 16 can aggregate real search/impression/review/assistant/circulation records.
External provider failure records are distinguished from successful assistant turns.
