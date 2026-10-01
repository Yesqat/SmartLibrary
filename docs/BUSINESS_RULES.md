# Business rules and circulation design

PHASE 11 makes the seven database policy settings editable by Admin with strict
validation, atomic updates and stale-version rejection. Subsequent operations use
new values immediately; existing due/expiry dates are preserved. Active Reader
circulation prevents role promotion until completed/cancelled. Blocking preserves
history and never prevents Librarian physical return. See ADMIN.md.

Status: catalog and PHASE 6 reservation/FIFO/QR generation are executable.
PHASES 7–8 reserved/direct issue and physical return/damaged/lost are executable.
Sources: PARTS 14–20, 27, 50, 57, 133, 137–143,
158–162 and acceptance B–I, Q–T. The unchanged Master Specification governs all rules.

## Reservation and allocation

PHASE 10 manual-number preview follows the same readiness/expiry/account/copy
checks as QR preview and produces a session-bound confirmation receipt. Both
require the separate explicit issue transaction. Operational dashboards use
LIBRARY_TIMEZONE day boundaries, and overdue always uses active loan due_at.
Reader profile/favorites/notification rules are documented in READER.md.

PHASE 4 catalog maintenance/archive rules are executable and documented in
[CATALOG.md](CATALOG.md). [RESERVATIONS.md](RESERVATIONS.md) records implemented
allocation/cancellation/expiration. Metadata edits cannot issue or return books.

Reader reserves BOOK. Allocate an eligible physical BOOK_COPY under a transaction. Select available copies deterministically by acquired_at with missing dates last, then created_at and id. FIFO queue order is reserved_at then id as a deterministic tie-break. An existing eligible waiter must not be bypassed by a new reservation or direct issue.

Validate current user ACTIVE, configured overdue restrictions and absence of a simultaneous active reservation for the same title. If a copy is available and no earlier eligible waiter claims it, create READY with assignment, ready_at, hold expiry, QR credential and notification. Otherwise create WAITING with no assigned copy or active pickup QR.

Queue eligibility is re-evaluated against current account/rules. Ineligible waiters remain WAITING and cannot block the first eligible waiter; do not silently cancel their reservations. Allocation/eligibility rechecks use the same domain service after copy availability or eligibility changes and in scheduled reconciliation. Persist/audit relevant skipped eligibility reasons safely.

## Explicit workflows

Reserved issue/verification are implemented as described in
[CIRCULATION.md](CIRCULATION.md), including the session-bound verification
receipt and PostgreSQL lock rechecks. PHASE 8 adds direct issue, return and loss;
the same document records their retry identity and exact state rules.

- QR verify: authenticated librarian, rate-limited token validation; READY, unexpired, ACTIVE reader, matching RESERVED copy. Return safe preview and audit. Do not change circulation state or create borrowing.
- Reservation issue: separate explicit librarian confirmation. Revalidate reservation/copy/user/limits/overdue inside transaction; create borrowing, complete reservation, invalidate QR, mark copy BORROWED and audit atomically.
- Direct issue: explicit librarian action, eligible ACTIVE reader, AVAILABLE copy, queue fairness and configured limits/overdue checks. Create borrowing with reservation_id null and mark copy BORROWED atomically.
- Return: librarian inventory lookup and condition inspection. BORROWED/OVERDUE becomes RETURNED with returned_at/returned_by. Acceptable copy goes to first eligible waiter or AVAILABLE. DAMAGED condition results in DAMAGED status and no allocation.
- Lost: validated librarian workflow makes active borrowing LOST and copy LOST atomically. It cannot be processed as a normal available return.
- Cancel: WAITING or READY becomes CANCELLED; invalidate QR. For READY, reassign the copy to the next eligible waiter or release it.
- Expire: expired READY becomes EXPIRED with invalid QR; same transaction reassigns/releases its copy and creates deduplicated notifications. WAITING has no pickup hold to expire.
- Overdue: active unreturned/nonlost borrowing with due_at < now. Authorization and analytics use the date even when the worker has not updated BORROWED to OVERDUE.

No terminal reservation is revived. No RETURNED borrowing is reused; subsequent borrowing creates a new record. Reader cannot issue or return. Copy maintenance/damage changes cannot orphan an active reservation or loan; staff workflows reconcile the related state atomically.

## Transactions and lock discipline

Plan a shared lock order for all circulation services: book row first (serialize its queue/copy allocation), involved user rows in UUID order, then reservation/copy/borrowing rows in deterministic order. Preliminary identity lookups must be revalidated after locks. Multi-book operations lock book IDs in order. Account/settings operations must not acquire locks in reverse order.

The user lock serializes limit checks across loans of different books. The book lock prevents reserve, direct issue, return, cancel and expire from claiming the same copy or jumping the queue. Do not use SKIP LOCKED to skip an earlier waiter within a title. Worker batches may skip a locked book and retry that book later. Lock queries and deadlock/retry behavior must be proven with real PostgreSQL concurrent tests before declaring circulation complete.

Use one transaction for state changes, relevant audit, domain interactions and in-app notification records. External work is dispatched after commit with durable pending-work recovery where needed; Redis failure must not lose committed embedding/notification work. Network/LLM calls never hold circulation locks.

Repeated issue/return/cancel must create no second operation. State checks and unique constraints provide minimum protection; request idempotency keys can return a prior result where useful. Safe conflicts are acceptable when a retry does not match the original request.

## Settings, dates and notifications

Read validated system settings for borrowing period, maximum books, reservation hold hours, return reminder days, pickup reminder hours and both overdue block flags. Development defaults 14/5/48/2 are configuration data, not service constants. Settings changes affect subsequent operations; existing due dates and holds retain their recorded deadlines unless a separately authorized workflow changes them.

Use one UTC clock value per transaction. READY is valid only while expires_at > now. At equality reject pickup and process expiration. User-facing/report dates use an explicitly configured library timezone.

Deduplicate notifications by entity, event type and logical reminder threshold/date or lifecycle event. Notification text belongs to the notification service/localization layer. Navigation uses safe entity types/IDs, not arbitrary redirect URLs.


PHASE 22 re-executed the full PostgreSQL circulation/concurrency/settings/worker
coverage. FINAL_ACCEPTANCE_MATRIX.md maps B–I and Q–T to actual evidence.
