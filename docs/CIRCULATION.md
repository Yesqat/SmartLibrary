# Librarian circulation

PHASES 7–8 implement reserved/direct issue and physical return/damaged/lost.
Camera scanning and reservation-number fallback
join the operational panel in PHASE 10. No Reader issue/return operation exists.

## Verified pickup followed by explicit issue

`POST /api/v1/librarian/qr/verify` accepts `{token}`. LIBRARIAN permission,
Bearer session and allowed Origin are required. Redis limits are 60 per user
and 120 per client IP per minute. Lookup uses SHA-256; token/hash never enters
audit/logs. The transaction locks the book and sorted involved users, rechecks
the credential and reservation, ACTIVE Reader, deadline and matching RESERVED
physical copy. It returns a safe preview with name, title, inventory number,
shelf, display reservation number and expiry. No phone/email/password or raw
QR is returned. Verification only writes a safe audit, never a borrowing.

Successful preview also carries a signed receipt valid for at most ten minutes
and never beyond the pickup deadline. It is bound to the Librarian identity and
session, reservation, Reader and assigned copy. A purpose-derived HMAC key,
fixed HS256 algorithm and distinct audience/type separate it from login tokens.
The receipt enforces the preview step at the API boundary as well as in the UI.
It stays in component memory; no URL/browser storage. Expired/mismatched receipts
return PICKUP_VERIFICATION_REQUIRED and require another verification.

`POST /api/v1/librarian/reservations/{id}/issue` accepts
`{verification_token}` and is a distinct explicit operation. It locks BOOK,
involved users in UUID order, reservation and copy. It rechecks session/role,
assignment, READY/deadline, ACTIVE Reader, real active loan count and overdue
due_at against current PostgreSQL settings. The Reader lock serializes limits
even for simultaneous issues of different titles. A successful transaction:

1. Creates Borrowing with due_at from borrow_period_days.
2. Completes reservation with completed_at and clears all QR columns.
3. Sets physical copy BORROWED.
4. Writes BOOK_ISSUED audit and deduplicated BORROW interaction.

Failure rolls everything back. Repeating the same verified issue by the same
Librarian returns its original borrowing while the receipt remains valid. A
different Librarian receives RESERVATION_ALREADY_COMPLETED. Neither can create
a second borrowing. Existing PostgreSQL reservation/copy uniqueness and composite
ownership FKs remain in force. No new schema or migration was needed.

Blocked/inactive status and borrowing-limit/overdue changes between verification
and issue are authoritative. Verification is a preview, not a promise of later
eligibility. An expired/cancelled/completed QR cannot be verified again.
Failures are safely audited separately after rollback. Successful operations
record no secrets. All Librarian responses have Cache-Control: no-store.

## UI and evidence

`/librarian/qr` accepts scanner/pasted QR text, displays the real preview and
explicitly says the book is not yet issued. Only a separate confirmed Issue
button invokes the issue API. Pending protection, expired-preview messaging,
safe errors and successful due-date display are in Kazakh. Catalog/reservation/
borrowing queries are invalidated after success. The Reader interface is unchanged.

PHASE_7_REPORT.md records PostgreSQL/security/concurrency and browser evidence.
Browser tests create dedicated development records and genuine loans; return
uses the actual workflow, not direct database cleanup.

## Direct issue and physical inventory lookup — PHASE 8

`POST /api/v1/librarian/borrowings` takes user_id, book_copy_id and UUID
idempotency_key. It requires LIBRARIAN, Bearer, Origin and a 60/user/minute Redis
limit. Current ACTIVE Reader, non-archived AVAILABLE copy/title, borrowing limit
and overdue settings are checked under the shared book/sorted-user/copy locks.
An eligible WAITING reader prevents direct issue from jumping the queue. Normally
copy availability transitions already allocate waiters; a legacy or newly
eligible queue awaiting reconciliation safely returns RESERVATION_QUEUE_CONFLICT.
PHASE 18 schedules that reconciliation rather than granting a fairness bypass.

Direct issue derives Borrowing.id as UUIDv5 of a fixed operation namespace plus
Librarian ID and caller retry UUID. This persists deduplication through restarts
using the existing PostgreSQL primary key. The locked Librarian serializes key
reuse even across different books. Same key/Reader/copy returns the original
borrowing, including its current terminal status; a changed payload conflicts.
A fresh intentional loan requires a new key. No ephemeral cache or new migration.
The ID is an identifier, not an authorization secret. New loans have no
reservation_id; due date, audit and BORROW interaction commit with copy BORROWED.

`GET /api/v1/librarian/borrowings/by-inventory/{inventory_number}` returns safe
book/copy metadata plus the current active borrowing, or null. Exact inventory
lookup is parameterized and bounded to 100 characters. Reservation QR and
physical inventory numbers remain distinct concepts.

`GET /api/v1/librarian/readers` provides bounded Reader name/email search for
staff selection, with account status and no auth secrets. `GET /librarian/
borrowings/overdue` uses active loan due_at < now, regardless of persisted
BORROWED versus OVERDUE. Reader GET `/api/v1/borrowings/me/active` and `/me/history`
are owner-scoped and paginated. History contains RETURNED/LOST records; all
responses include safe title/inventory metadata and computed is_overdue.

## Return, damage and loss

`POST /api/v1/librarian/borrowings/{id}/return` accepts only an inspected
CopyCondition. It changes an active loan to RETURNED with timestamp/operator.
An acceptable condition makes the copy AVAILABLE, then the shared FIFO service
assigns it to the next eligible waiter in that transaction. The returned copy
is preferred. DAMAGED sets both condition/status DAMAGED and stays unavailable.
Return also reconciles elapsed READY holds for that title. Accounts that are
blocked or inactive can still physically return through the Librarian.

`POST /api/v1/librarian/borrowings/{id}/lost` marks an active loan LOST with
lost_at and copy LOST. It cannot become an available return. Both mutations
require Librarian/Origin and use Redis limits. Terminal repeats acknowledge the
original result without further copy mutations or audit events; a return after
loss or loss after return conflicts. Retrying an old return cannot alter a newer
loan of the same copy. State checks, book locking and active-copy uniqueness
prevent double issue. Audit captures return condition and lost/damaged events.

Staff pages `/librarian/issue` and `/librarian/return` use real inventory lookup,
Reader selection, inspection/confirmation, duplicate-submit protection, safe
errors and Kazakh success/due-date feedback. Input changes clear old actionable
results. Reader pages have no physical return operation. Full Reader UI is PHASE 9.
