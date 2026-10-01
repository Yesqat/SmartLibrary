# Analytics — PHASE 16

Six ADMIN-only GET endpoints under `/api/v1/admin/analytics`: overview,
circulation, inventory, readers, search and ai. Each uses a read-only repeatable-read
PostgreSQL snapshot, a 10-second SQL statement timeout, no-store responses and
60 requests per account/minute. No source data is changed and no full table is
loaded into Python. SQL counts/grouping/joins provide all metrics.

## Dates and current state

`date_from`/`date_to` are inclusive calendar dates in configured LIBRARY_TIMEZONE.
SQL uses local midnight through the exclusive next midnight. Default: last 30 days;
maximum: 3660 days, years 1900–9998. Invalid ranges/extra parameters return 422.
Daily buckets cover up to 60 days, weekly up to 365, monthly beyond that.
Week starts Monday; first/last buckets may be partial. Missing activity is zero.
Every response returns the period, timezone, grouping and generation timestamp.

Current counts are explicitly snapshots, irrespective of date filters:
nonarchived book titles; nonarchived copies of nonarchived books; all six copy
statuses; active loans (BORROWED/OVERDUE, neither returned nor lost); overdue
active loans with due_at before generation time; WAITING/READY reservations;
current READER accounts and their ACTIVE-status subset.

Period metrics: added titles/copies by created_at (including subsequently archived
records); loans by borrowed_at, returns by returned_at, losses by lost_at;
reservation creations by reserved_at and terminal transitions by completed_at,
cancelled_at or expires_at for EXPIRED records. Completion percentage is
completed / (completed + cancelled + expired), excluding still-active records.
Reservation cohort status groups records created in the period by current status.

Popular books/categories count actual loans issued in the period, top ten.
Categories reflect current catalog classification; a multi-category book counts
once in each assigned category. This circulation measure differs intentionally
from the PHASE 13 multi-signal recommendation ranking.

Active Readers are distinct current READER accounts with a recorded interaction,
search, issue/return, reservation creation/cancellation/completion or USER assistant
message in the period. Passive impressions and login alone do not qualify.
Registration counts include currently-READER accounts created in the period.

## Search, AI and recommendation measurement

Search counts use persisted search_events; zero-result rate uses result_count=0,
with STANDARD/SEMANTIC/HYBRID groups, continuous trends and top 15 zero-result
query strings. No invented usage or user identities are returned.

Prediction/run counts use creation time. Review counts/outcomes use review time.
Acceptance = accepted predictions / reviewed predictions; this is not ML accuracy.
Reproducible held-out quality remains in CATEGORIZATION.md and its evaluation file.

Assistant questions are USER messages; successes/failures are ASSISTANT messages
with absent/present error_code. Distinct conversations/readers use USER activity.
Average latency and token totals use stored provider measurements only; unknown
token counts remain null and their response count is reported separately.

Recommendation CTR uses impressions actually rendered during the period and
distinct corresponding recorded clicks by generation time, including a later
click on an in-period impression. A click whose impression is outside the period
is excluded. Unique ownership/attribution constraints prevent duplicate clicks.
No-impression CTR is null, not zero; all three recommendation modes are separate.

## UI, schema and evidence

`/admin/analytics`, `/admin/ai` and Dashboard charts use Recharts, Kazakh labels,
zero-based count axes, legends/tooltips, accessible data tables and loading/error/
retry/empty states. Overview refreshes every minute; other tabs refresh on normal
query focus/refetch, and new date filters create new queries. No server result cache.

Migration 0004 adds nine date indexes for reservations, lost loans and prediction
creation/review. Model/migration drift and isolated fresh upgrade/downgrade/upgrade
passed. Live database has 144 indexes including Alembic's own PK (143 domain
indexes). An actual ten-loan aggregate EXPLAIN used a one-page sequential scan,
0.065 ms execution; this is a small development sample, not a scale benchmark.

Tests compare API values with real PostgreSQL state, including backdated fixtures,
timezone boundaries, zero denominators, real circulation, overdue-before-worker,
review/assistant telemetry, attributed CTR and negative RBAC. See PHASE_16_REPORT.md.
