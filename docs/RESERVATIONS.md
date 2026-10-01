# Reservations and Reader QR

Implemented across PHASES 6–8 and 18, including periodic scheduling. BOOK and BOOK_COPY remain separate.

## API

All routes below use `/api/v1/reservations`, require READER, enforce ownership
with 404 for another owner, and return `Cache-Control: no-store` even on errors.

| Method/path | Behavior |
|---|---|
| POST / | Body only book_id; returns 201 READY or WAITING; no caller-selected user/copy/status |
| GET /me | Owner pagination, maximum 100, optional status, latest first |
| GET /{id} | Safe detail, title, status, dates, position and qr_available; no secret |
| POST /{id}/cancel | Origin-checked cancellation, atomic queue advancement, idempotent terminal result |
| GET /{id}/qr | READY/unexpired owner credential, PNG data URL and deadline; validates RESERVED copy |

The existing PostgreSQL sequence generates unique `R-<sequence>` display
numbers. These are not credentials. Duplicate active owner/title reservations
conflict; a completed reservation cannot be cancelled.

## Transactions and fairness

Lock BOOK, then all active reservation owners plus actor in UUID order, then
reservation/copy rows. Recheck live session/account/role in the transaction.
Creation inserts WAITING before allocation. FIFO uses reserved_at then id.
Temporarily ineligible account/overdue waiters remain WAITING and are skipped
with a safe audit reason. Displayed position includes all WAITING records.

Copy selection uses acquired_at (null last), created_at, id. Only non-archived,
non-damaged AVAILABLE copies qualify. Released copies are preferred during
cancellation/expiration. New/restored/repaired copies immediately serve existing
waiters through the same service. Partial unique constraints remain the final
guard for active owner/title and READY/copy assignment.

READY gets copy assignment, ready_at, expiry, encrypted QR and notification in
the same transaction. Cancellation/expiration retains historical assignment and
dates, clears all QR columns, then reassigns/releases inventory. Audit, RESERVE
interaction and notifications commit together. Notifications deduplicate on
user + event type + reservation ID. Missing QR configuration rolls allocation back.

Settings are read from PostgreSQL on every transaction, without duplicated
service defaults or an application cache. reservation_hold_hours sets new holds;
existing deadlines remain unchanged. block_reservation_if_overdue uses active
BORROWED/OVERDUE loans with due_at < now, independent of the worker. Borrowing
limits apply at issue, not as an invented reservation limit.

Creation/cancellation reconcile elapsed READY holds for that title. The shared
expiration transition runs every 60 seconds through Celery Beat. Eligible waiting
Readers are also reconciled with available copies. See BACKGROUND_JOBS.md. GET does not mutate circulation. Past-deadline READY has no usable
QR even before its persisted state is reconciled. All dates use aware UTC.

## Credential boundary

QR_ENCRYPTION_KEY is the independent URL-safe base64 32-byte Fernet key created
by scripts/init_env.py. Credentials contain 256 random bits; PostgreSQL stores
SHA-256 lookup hash, Fernet ciphertext and a key fingerprint. Ordinary DTOs and
logs omit these fields. Terminal states clear them. The development-v1 seed
label remains recoverable with its original key. Keep that key backed up;
changing it requires a deliberate re-encryption plan for existing READY rows.
Missing/invalid keys fail closed with QR_SERVICE_UNAVAILABLE.

PNG generation uses [qrcode 8.2](https://pypi.org/project/qrcode/) and Pillow with
a four-module quiet zone. Owner display is explicit, in memory only, hidden at
expiry and removed after cancellation/logout. No token-bearing URL or browser
storage. Redis permits 30 creates, 60 cancellations and 60 QR reads per user per
minute; dependency failure fails closed through the standard error contract.

## UI and verification

Book Details offers login/reserve/queue. Protected `/reservations` and
`/reservations/{id}` show actual data, private QR, confirmation-based cancellation,
loading/empty/error/retry states and Kazakh labels. Mutations invalidate catalog
and reservation queries. Lists/details refresh every 30 seconds. No Reader issue
or return action exists. PHASE_6_REPORT.md records executed evidence and limits.
