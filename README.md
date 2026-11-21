# SmartLibrary

A Kazakh-first system for a physical library: catalog, circulation, Reader and
staff workflows, multilingual retrieval, reviewed ML and database-derived reporting.

## Authority and status

MASTER_SPECIFICATION.md is the immutable contract for PHASES 0–22.
**PROJECT COMPLETE — FINAL VERIFICATION PASSED.**
All executable applicable checks passed. The [AI librarian guide](docs/AI_ASSISTANT.md#verification)
records the subsequent live Groq check. Public hosting remains an operator requirement. See the
[final report](docs/FINAL_IMPLEMENTATION_REPORT.md), [A–X acceptance matrix](docs/FINAL_ACCEPTANCE_MATRIX.md)
and [final reviews](docs/FINAL_REVIEWS.md) for evidence and measured limitations.

## Features

- BOOK titles and separate physical BOOK_COPY inventory; live availability,
  authors/categories/publishers, validated covers, shelf/condition/status and archive.
- Argon2id, memory-only access tokens, rotating HttpOnly refresh sessions, CSRF,
  backend role/ownership checks, Redis rate limits and immutable audit history.
- Reader reserves a title; PostgreSQL safely assigns a copy or FIFO waiting place.
  Private QR verifies a reservation. A Librarian explicitly issues the book.
- Direct issue, physical return, damaged/lost handling, queue advancement,
  configurable limits/overdue restrictions, notifications and scheduled reminders.
- Reader dashboard, favorites, reservations/QR, loans/history, interests/profile;
  Librarian camera/manual scanner and operations; Admin management/settings/audit.
- Exact/metadata/fuzzy search, filters, server pagination, E5 multilingual pgvector
  semantic search and RRF hybrid search. Real popular/similar/personal recommendations.
- TF-IDF/OVR and embedding categorization with human review and reproducible metrics.
  Controlled AI Librarian tools and owned conversation history; external LLM optional.
- Recharts analytics and actual PDF/XLSX inventory, loan, overdue and reservation reports.

Physical books only. Reader never marks a physical return. QR never auto-issues.

## Architecture

Next.js 16 / React / TypeScript / Tailwind / shadcn-style Radix components /
TanStack Query / Recharts connect through Nginx to the FastAPI modular monolith.
SQLAlchemy/Pydantic/Alembic manage PostgreSQL 17 with pgvector and pg_trgm.
Redis supports rate limits and Celery; default worker, ML worker and Beat share
backend services. There are 27 tables, 16 enums and five migrations through
0005_reservation_reminder. Python and npm lockfiles and image digests are pinned.

## Requirements and development startup

Docker Desktop Linux engine/Compose 2.24.4+ (verified 29.8.0/5.5.1), Python 3.13;
native work also uses Node 24 and uv. From C:\SmartLibrary:

```powershell
python scripts/init_env.py
docker compose build backend frontend
docker compose up -d --wait postgres redis
docker compose run --rm database python -m app.db.manage upgrade
docker compose run --rm database python -m app.db.manage check
docker compose run --rm database python -m app.db.manage seed
docker compose up -d --wait --wait-timeout 180
```

init_env.py refuses to overwrite .env. Existing phase-one environments can use
init_database_env.py to add missing role settings. Never print or commit secrets.
Migrations are explicit; startup does not create tables. Seeds are repeat-safe and
development/test only. Account names are admin, librarian, reader1–reader4 at
smartlibrary.example; their password is private DEV_SEED_PASSWORD, not a default.

- Frontend: http://localhost:8080
- API docs: http://localhost:8080/docs (development/test only)
- Backend liveness/readiness: /api/v1/health and /api/v1/ready

For reload, apply `-f docker-compose.yml -f docker-compose.dev.yml` consistently to
build/up/operator commands. Only Nginx publishes a port. PostgreSQL/Redis stay
private. Do not use `down -v` for routine restarts; it deletes persistent data.

## Embeddings and ML

```powershell
docker compose run --rm backend python -m app.ai.embeddings.cli download
docker compose run --rm backend python -m app.ai.embeddings.cli generate
```

The first command needs network access and downloads the pinned multilingual E5
base revision; subsequent inference is local. The ML worker and Beat reconcile
metadata edits and interrupted generation. For model benchmarking and training:

```powershell
$env:HF_HOME='C:/SmartLibrary/work/model-cache'
backend/.venv/Scripts/python.exe ml/evaluation/benchmark_search.py --download
$env:PYTHONPATH='C:/SmartLibrary/backend'
$env:MODEL_CACHE_DIRECTORY='C:/SmartLibrary/work/model-cache'
$env:HF_HUB_OFFLINE='1'
backend/.venv/Scripts/python.exe -m app.ai.categorization.training --dataset ml/data/categorization.json --metrics ml/evaluation/categorization_results.json
```

Deploy generated categorization/model.json into the Docker model volume as
documented in CATEGORIZATION.md. The small curated corpus is insufficient to claim
general ML accuracy: categorization has only two held-out books. Collaborative
serving remains disabled when real loan history is insufficient; content-based
and cold-start recommendations work independently.

## External configuration and production

The AI librarian supports GroqCloud and OpenAI. For Groq, set `LLM_PROVIDER=groq`,
`LLM_MODEL=openai/gpt-oss-120b` and a private `GROQ_API_KEY` in the project’s
`.env`. Apply the change with `docker compose up -d --build --no-deps backend`.
Readers can then ask about the live catalog in Kazakh, Russian or English.
See the [assistant setup and verification guide](docs/AI_ASSISTANT.md).

Use [production setup](docs/PRODUCTION_DEPLOYMENT.md) for independent credentials,
first Admin, HTTPS, trusted certificate/domain and deployment checks. Local TLS
verification does not constitute public deployment. See
[backup/recovery](docs/BACKUP_RECOVERY.md) for actual pg_dump/pg_restore and image/
artifact recovery; Docker volumes are not backups.

## Tests and documentation

[TESTING.md](docs/TESTING.md) gives exact native, PostgreSQL, browser, ML and Docker
commands. [TEST_MATRIX.md](docs/TEST_MATRIX.md) maps critical behavior to tests.
Only the external provider boundary is mocked in assistant integration tests;
circulation/concurrency/vector tests use real PostgreSQL.

- [Architecture](docs/ARCHITECTURE.md), [database](docs/DATABASE.md), [schema](docs/SCHEMA_REFERENCE.md)
- [Business rules](docs/BUSINESS_RULES.md), [API contracts](docs/API_SPEC.md), [endpoint inventory](docs/API_ENDPOINTS.md)
- [AI architecture](docs/AI_ARCHITECTURE.md), [semantic search](docs/SEMANTIC_SEARCH.md), [recommendations](docs/RECOMMENDATIONS.md)
- [Categorization](docs/CATEGORIZATION.md), [AI assistant](docs/AI_ASSISTANT.md)
- [Security](docs/SECURITY.md), [authentication](docs/AUTHENTICATION.md), [UI routes](docs/UI_SITEMAP.md)
- [Analytics](docs/ANALYTICS.md), [reports](docs/REPORTS.md), [background jobs](docs/BACKGROUND_JOBS.md)
- [Deployment](docs/DEPLOYMENT.md), [implementation order](docs/IMPLEMENTATION_PLAN.md), [coverage](docs/SPECIFICATION_COVERAGE.md)

PHASE_0_REPORT.md through PHASE_22_REPORT.md are historical execution records.
Their phase-specific counts do not represent the current complete test suite.
