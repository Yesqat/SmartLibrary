# Librarian operational panel

PHASE 10 builds on the existing catalog/circulation/Reader modules.

## Pages and queries

- `/librarian`: issued/returned today, new/active reservations, actual overdue count,
  latest ten allowlisted circulation audit events and operational shortcuts. Today's
  interval is [local midnight, next midnight) in LIBRARY_TIMEZONE, shown in the UI.
  SQL aggregation is used; no fabricated numbers or whole-table Python counting.
- `/librarian/readers`: bounded name/email/UUID search and status filter.
  `/librarian/readers/{id}`: safe contact/status fields, current count/limit,
  overdue count, prospective due date, active/history borrowings and reservations.
  No password/token/session/AI-conversation data is returned.
- `/librarian/reservations`: bounded number/title/Reader search and status filter;
  dates, state, queue position and Reader link, without QR secrets.
- `/librarian/overdue`: current due_at-based overdue, text filter across book/Reader/
  inventory, minimum days and oldest/newest/Reader sorting, Reader links and actual
  dates. The page never clears overdue directly. Reminders are scheduled in PHASE 18.
- Existing books/editor/references/copy management remain shared working pages.
  Direct issue now previews current eligibility/limit and calculated due date;
  the actual issue transaction rechecks all rules. Reader selection locks after
  success until a fresh inventory lookup. Return displays inspected condition,
  original dates/status and the actual resulting copy state fetched after commit.
- Shared `/account/profile` supplies Librarian profile/avatar/password access.
  Role/status/settings administration is never exposed as a Librarian mutation.

## QR and manual lookup

`/librarian/qr` uses pinned @zxing/browser 0.2.1, dynamically loaded for camera
scanning. It requests video only, prefers the rear camera, decodes locally and
sends only the decoded credential to the existing verification API. Tracks stop
after a result, cancellation, page exit or a late permission response after exit.
Denied/unavailable camera has safe Kazakh guidance; manual/pasted input stays usable.

The [official ZXing browser documentation](https://github.com/zxing-js/browser/blob/master/README.md)
describes stream decoding and scanner controls. No camera frames are uploaded.
Actual camera use requires a supported browser, camera permission and a secure
context (HTTPS, or localhost in development). Physical-device interoperability
still depends on the user's device; browser verification used actual QR pixels
through a controlled MediaStream and the real decoder, not fabricated scan results.

POST `/api/v1/librarian/reservations/verify-number` accepts an exact reservation
number for authenticated LIBRARIAN. The UI directs the Librarian to check the
Reader's identity. It uses the same lock order, current account, READY/expiry,
copy consistency and signed session-bound receipt as QR verification. It returns
no stored QR secret. QR and number verification share the same Redis limits.
Safe audit actions distinguish manual verification/failure from QR verification.

Neither verification path creates a borrowing or changes physical/reservation
state. Only the separate confirmed issue endpoint does. Preview shows Reader,
title, reservation number/state, expiry, inventory and shelf. Receipts remain in
component memory and expire; every issue checks live state again.

## API additions

GET `/api/v1/librarian/dashboard`, `/readers/{id}`, `/readers/{id}/borrowings`,
`/reservations`; POST `/reservations/verify-number`. Existing `/readers` adds
status/UUID search; `/borrowings/overdue` adds q/minimum_days/order filters.
All require Librarian permission. Admin remains a distinct role with its own
monitoring endpoints in PHASE 11, not implicit circulation privileges.

No database model/migration changes. AI-assisted category review is implemented in PHASE 14;
this phase does not advertise a simulated categorization control.
