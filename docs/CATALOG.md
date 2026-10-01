# Catalog implementation

PHASE 4 implements physical catalog metadata and inventory. It uses the existing
27-table schema, runtime database role, bearer authentication and audit writer.
No migration or previously applied migration was changed.

## Reads and availability

`GET /api/v1/books` returns `items/page/page_size/total/pages`. Pages default to
20 and are limited to 100. This staff listing's `q` performs escaped
case-insensitive title containment. PHASE 5 implements complete public ranking,
filters and fuzzy search at `/api/v1/search`; see [SEARCH.md](SEARCH.md).
`GET /books/{id}` returns a safe bibliographic DTO with authors, categories and
publisher. Archived titles are hidden by default. Staff can request
`include_archived=true`; anonymous and Reader access to that option is rejected.

Availability comes from an aggregate over non-archived BOOK_COPY rows. The public
response contains total_copies, available_copies and distinct shelf locations of
available copies. Archived titles expose zero available copies. A page uses four
queries: count; titles with copy aggregate/publisher; authors; categories. It
does not issue one availability query per title. Inventory-number and individual
copy metadata listing is restricted to catalog staff.

## Mutations

Both LIBRARIAN and ADMIN have MANAGE_CATALOG. Every mutation checks a bearer
credential and allowed Origin. The service rechecks the live session, ACTIVE
account and current database role inside the transaction before writing. Auth
cookie routes retain their PHASE 3 CSRF proof; domain routes never authenticate
through a cookie, so they do not depend on the refresh cookie's narrow path.

- POST/PATCH books: title, ISBN, description, year, language, page count and
  existing active author/category/publisher links. ISBN-10/13 is normalized and
  checksum-validated. Unknown fields and null mandatory values are rejected.
- GET/POST books/{id}/copies and PATCH copies/{id}: unique inventory number,
  per-copy shelf, acquisition date, condition and permitted maintenance state.
- GET/POST authors, categories, publishers; PATCH each /{id}: bounded reads
  and metadata edits. Relations use actual UUIDs, never browser-supplied objects.
- PATCH books/{id}/archive, copies/{id}/archive and each taxonomy /{id}/archive:
  `{archived: true|false}`. These preserve rows and historical foreign keys.
- POST books/{id}/views: READER only, `{event_id: UUID}`. The authenticated user
  is derived on the backend. A user/event key deduplicates retry submissions.
  Only displayed Reader detail visits are recorded; anonymous/staff reads and
  prefetches do not manufacture Reader interactions.

Book/copy writes serialize on the parent BOOK row. Reference records are locked
while validating links. Future circulation workflows must acquire the same book
lock before allocating/changing copies, then lock affected users/copies in a
consistent order. This avoids archive/allocation races. Database uniqueness is
the final defense against concurrent ISBN/inventory/category collisions.

## Lifecycle

Book archive is rejected while WAITING/READY reservations or active physical
loans/assignments exist. Taxonomy archive is rejected when a non-archived title
references it. Restoring a title requires active taxonomy references. Active
borrowing/READY assignment or RESERVED/BORROWED copy status blocks metadata
mutation/archive of that copy. There is no metadata operation that issues or
returns a physical book. No hard-delete endpoint is exposed.

Maintenance transitions are centralized in `services/copies/state.py`:
AVAILABLE → DAMAGED/LOST/MAINTENANCE; DAMAGED → MAINTENANCE;
MAINTENANCE → AVAILABLE/DAMAGED/LOST. Repair requires a non-damaged condition
before availability. Initial damaged stock starts DAMAGED. LOST cannot be reset
to available through metadata editing. Circulation transitions are added in
their owning phases. Important writes append transactionally to audit_logs.

## Images

POST books/{id}/cover accepts a multipart `file`; DELETE removes the cover.
JPEG/PNG/WEBP only, maximum 5 MiB, minimum side 16, maximum side 6000 and at most
16 million decoded pixels. Declared MIME must match decoded format. Malformed,
animated and decompression-bomb images are rejected. Pillow verifies and decodes
the image, applies orientation, strips metadata and re-encodes RGB WEBP with a
maximum 2400-pixel edge. Original filenames are ignored. Names are random UUIDs.

The storage protocol has a local adapter rooted at UPLOAD_DIRECTORY, outside
application code. Only generated names can be resolved through GET
`/api/v1/media/{uuidhex}.webp`; clients never receive local paths. Immutable image
URLs are cacheable; replacements get new URLs. New files are cleaned on database
rollback. After commit, the previous file is removed only when neither a book
nor an avatar references it. Default/external URLs are never removed.

Crash leftovers can be reviewed with:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m app.services.storage.cleanup
```

Add `--apply` to delete only unreferenced generated files older than 24 hours.
The grace window excludes concurrent new uploads. Symlinks and unknown names are
excluded. Production object storage can implement the same storage boundary;
it is not required for local development. Nginx caps total requests at 10 MiB.

## Frontend

Public `/catalog` and `/books/{id}` use real paginated APIs, Book Cards, cover
fallbacks, current availability and safe loading/error/empty states. Both
`/librarian` and `/admin` provide `/books`, `/books/new`, `/books/{id}`,
`/books/{id}/copies` and `/references` behind existing protected layouts.
Reference pickers search bounded backend pages with debounce. Forms prevent
duplicate submissions; archive, cover removal and copy-state changes require
confirmation. Mutations invalidate catalog queries so availability refreshes.
Kazakh labels and safe errors are centralized. Full role dashboards and
circulation screens remain in their assigned phases.


## Optional import and barcode extensions

PART 169 makes bulk import optional. No bulk importer is claimed. The reusable
validated catalog/copy services and constraints can be called by a future
transactional batch adapter; it must report row errors and reject duplicate ISBN/
inventory identifiers. PART 143 physical barcode lookup can use the existing
inventory-number lookup; reservation QR credentials remain separate.
