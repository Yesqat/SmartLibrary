# Reader self-service

Implemented in PHASE 9 using existing authentication and domain services.

- `/dashboard`: owned SQL counts, nearest due date, overdue warning, current loans,
  active reservations and valid READY QR shortcuts. One statement computes counts;
  no full-table loading. Active loans sort by due date.
- `/my-books`, `/history`: paginated owned borrowings, inventory number, dates,
  status and title links. Overdue uses due_at before worker status updates.
  Reader has no physical-return operation; instructions direct them to the library.
- `/reservations`: active/history server filters, dates, state, queue and QR links.
- `/favorites`: owned paginated titles with aggregate current availability.
  Add/remove is idempotent. Only an actual new favorite creates a FAVORITE event;
  duplicate adds do not inflate events. Remove/re-add records a new actual event.
  Archived favorites remain visible/removable with zero reservable availability.
- `/notifications`: owned all/unread lists, mark-one and mark-all. Safe entity
  type/UUID maps to controlled frontend routes. No arbitrary redirect URL or secret.
  Read-all affects existing owned rows; subsequently created notifications remain unread.
- `/account/profile`: each authenticated role can update its own names/phone/avatar.
  Email is deliberately read-only; email change/reset delivery is not configured.
  Role/status/created_at/history/avatar_url are forbidden profile input fields.
  Password change retains the existing secure account-security page.
- Avatar lifecycle reuses decoded JPEG/PNG/WEBP validation, generated WEBP names,
  storage abstraction, rollback cleanup and post-commit unshared-file cleanup.
  Profile/avatar audit events contain no values/secrets. Missing avatars show initials.
- Optional Reader interests use real active categories through bounded search.
  Atomic replacement allows at most 30 unique IDs, each with baseline weight 1;
  empty selection is valid. No hardcoded category catalog.

Ownership always derives from the principal. Domain writes require Bearer, Origin,
live-session recheck and Redis limits (120 Reader writes/minute; 30 profile writes/minute).
Private responses use no-store. Favorite locking follows book then user; preferences
lock ordered categories then user, matching catalog mutation ordering.

Relevant writes invalidate availability/favorites, reservations, notifications and
summary caches. Identity transitions continue to clear private query data.
Real recommendation/popular sections, Assistant and scheduled reminders are
implemented in PHASES 13, 15 and 18. External LLM configuration remains optional
for core circulation; unavailable AI returns a safe error.
