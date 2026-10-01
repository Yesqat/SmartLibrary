# Implemented UI sitemap

Primary UI language is Kazakh. Next.js pages use real typed APIs and shared
feature components. Protected role layouts and query state handling are UX;
backend authorization remains authoritative. Final page traversal is in
tests/e2e/pages.spec.ts; individual workflow tests exercise mutations and errors.

| Audience | Routes and behavior |
|---|---|
| Public | / (popular books/search), /catalog (standard/semantic/hybrid, filters/pagination), /books/{id} (details, availability, similar books), /login, /register |
| Reader | /dashboard (summary/recommendations), /assistant (owned conversation history/tools), /favorites, /reservations (active/history), /reservations/{id} (READY QR, FIFO/status/cancel), /my-books, /history, /notifications |
| All active roles | /account/profile (names/phone/avatar; Reader preferences), /account/security (password/sessions) |
| Librarian | /librarian, /librarian/qr, /librarian/books, /librarian/books/new, /librarian/books/{id}, /librarian/books/{id}/copies, /librarian/references |
| Librarian operations | /librarian/issue, /librarian/return, /librarian/reservations, /librarian/readers, /librarian/readers/{id}, /librarian/overdue, /librarian/category-predictions |
| Admin management | /admin, /admin/users, /admin/users/{id}, /admin/librarians, /admin/books, /admin/books/new, /admin/books/{id}, /admin/books/{id}/copies, /admin/references |
| Admin inventory/rules | /admin/authors, /admin/categories, /admin/publishers, /admin/inventory, /admin/borrowings, /admin/reservations, /admin/settings, /admin/audit-logs |
| Admin intelligence | /admin/analytics (overview/circulation/inventory/readers/search/AI), /admin/ai, /admin/category-predictions, /admin/reports |

QR is an owned view inside Reservation Details; profile is shared by active roles.
Add/edit/copy pages share feature components between authorized staff layouts.
Current backend permissions remain explicit: Admin management does not silently
grant Librarian circulation capability.

## Interaction rules

- Login/register validate fields, provide pending/safe errors and prevent duplicate
  submission. Public registration has no role selector. Login return paths are local.
- Catalog queries/filter changes are server-driven and reflected in URLs. BookCard
  uses aggregate current copy availability, safe cover fallback and accessible links.
- Reader reserves BOOK, sees queue/READY status and private QR. My Books provides
  physical-return instructions, with no Reader return mutation.
- Camera decoding and manual reservation lookup show a verified preview. Only a
  separate confirmed Issue action creates borrowing. Camera denial/unavailability
  retain manual input. Return requires inventory lookup and inspected condition.
- Important cancellations, archival, issue/return/loss, role/status and category
  review operations require confirmation. Forms disable pending actions and update
  affected queries on success. Settings use optimistic conflict detection.
- Notifications support owned read/read-all; profile cannot change role/status/history.
- Categorization displays actual score provenance and requires a final existing
  category selection. Assistant cards use real IDs and normal reservation links.
- Analytics charts have titles, labels, tooltips and accessible tables. Date ranges
  and metric definitions are visible; reports provide actual private downloads.
- Major queries/forms have loading, empty, safe error/retry and permission states.
  Mobile Reader/QR layouts and scrollable staff tables retain keyboard labels and
  focus controls. Non-color status text complements badges.

Nonce CSP, browser permission policy and backend error contracts apply across pages.
No production mock backend, fabricated counts or invented availability populate UI.
