# Background processing

PHASE 18 implements real Celery/Redis jobs. One Beat process dispatches both
circulation maintenance and missing embeddings every 60 seconds. Default and ML
queues have separate workers; inference cannot occupy circulation capacity.

## Circulation sweep

`smartlibrary.circulation.sweep` selects at most 200 IDs per category (service
limit 1–1000). Each item commits independently using Book, sorted User, then
reservation/copy/borrowing locks. Requests and jobs share the same domain services.

- Expired READY holds become EXPIRED, erase QR material, audit and notify. The
  released copy serves the first eligible WAITING Reader or becomes AVAILABLE.
- Available copies and eligible WAITING Readers are reconciled, including after
  an account is unblocked or overdue eligibility is restored. FIFO is unchanged.
- READY holds nearing expiry get RESERVATION_EXPIRING. Database setting
  reservation_reminder_hours defaults to 6; zero disables it.
- Active loans nearing due_at get DUE_SOON using return_reminder_days. Overdue
  loans become OVERDUE and get OVERDUE once. Critical request rules and analytics
  use due_at directly; they do not wait for this persisted status update.

Notifications use unique `(user_id, TYPE:entity_id)` keys and owner foreign keys.
Dates are immutable for the current borrowing/hold lifecycle, so a notification
is sent once per type/entity even if the threshold changes. Selection excludes
already delivered events so old rows cannot starve a bounded batch.

## Recovery

Late acknowledgements, worker-loss rejection, three retries 60 seconds apart,
240/300-second soft/hard limits, per-item 3-second lock and 15-second SQL timeouts
bound failures. Transactions roll back partial expiration/allocation/notification.
Failures log only exception class and a safe retry code. Subsequent sweeps recover
remaining eligible work; duplicate dispatch and worker restart are safe.

Jobs return counts (expired, assigned, pickup_reminders, loan_notifications,
failed). Worker ping and Beat heartbeat are checked by scripts/verify_stack.py.
Beat is a single scheduler; additional workers are safe through database locks.
Notifications are in-app. Production SMTP is not required or falsely simulated.

Migration 0005 adds only the reminder setting; no tables or existing migrations
were rewritten. Admin changes affect subsequent transactions without a cache.
Embedding jobs retain their model/source-hash validation and dedicated queue.
