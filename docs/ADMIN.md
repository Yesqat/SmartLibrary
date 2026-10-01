# Administration

PHASE 11 adds real Admin management to the existing catalog and authentication
foundations. ADMIN is required on every administration endpoint. LIBRARIAN
retains physical circulation; ADMIN has no implicit issue/return permission.

## Accounts

Users and Librarians are searched and paginated in PostgreSQL by name, email,
UUID, role and status. Details expose safe profile fields and circulation links.
Public registration still creates READER; privileged assignment requires an
authenticated Admin role change and confirmation in the UI.

Role/status changes lock actor and target in UUID order, serialize Admin membership
decisions with a PostgreSQL transaction advisory lock, and preserve at least one
ACTIVE ADMIN. A Reader with active loans or reservations must finish those workflows
before promotion. Blocking preserves history and still permits Librarian physical
returns. Each actual change revokes all target refresh families; access requests
recheck the live account/session. Repeating the same change has no duplicate audit
or revocation side effect. Audits contain safe actor/target/reason data, never credentials.

## Settings

All seven circulation settings are read from the database, with database
type/bounds enforced on atomic batch updates. `expected_updated_at` prevents lost
updates; stale versions return SETTINGS_CONFLICT. The form retains its loaded
version while editing, including during background refetch. Reload explicitly
discards a draft after confirmation. Services read current settings for subsequent
operations; existing loan/hold deadlines are not retroactively rewritten. No
service defaults or settings cache duplicate the database policy.

## Monitoring and audit

Dashboard counts are one SQL aggregation over real records. Operational inventory
excludes archived books/copies; inventory can explicitly include archived records.
Overdue is active borrowing with due_at before the current time, independent of
worker status updates. Borrowing and reservation lists use server pagination and
safe shared projections. Audit history is read-only, filtered by local calendar
dates in LIBRARY_TIMEZONE, actor, action and entity. Date intervals are inclusive
in the UI and half-open instants in SQL. Only the approved short reason field is
returned from details; raw JSON/IP/session material is not exposed.

Catalog/editor/copies and author/category/publisher management reuse PHASE 4 APIs.
All pages use Kazakh labels, role protection, loading/error/retry/empty states and
relevant query invalidation. Security writes require Origin and Redis rate limits.

## Later owning phases

AI predictions/review: PHASE 14; AI overview and analytical charts: PHASE 16;
PDF/XLSX reports: PHASE 17. Those functions are not represented by fake dashboard
values or nonfunctional navigation in PHASE 11.
