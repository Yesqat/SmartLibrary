# API endpoint inventory

Generated from the checked OpenAPI contract. See API_SPEC.md for permissions,
ownership, errors and contract generation. Swagger is development/test only.

| Method | Path | Operation |
|---|---|---|
| GET | `/api/v1/admin/analytics/ai` | Ai View |
| GET | `/api/v1/admin/analytics/circulation` | Circulation View |
| GET | `/api/v1/admin/analytics/inventory` | Inventory View |
| GET | `/api/v1/admin/analytics/overview` | Overview |
| GET | `/api/v1/admin/analytics/readers` | Reader View |
| GET | `/api/v1/admin/analytics/search` | Search View |
| GET | `/api/v1/admin/audit-logs` | Audit |
| GET | `/api/v1/admin/borrowings` | Borrowings |
| GET | `/api/v1/admin/dashboard` | Dashboard |
| GET | `/api/v1/admin/inventory` | Inventory |
| GET | `/api/v1/admin/librarians` | Librarians |
| POST | `/api/v1/admin/reports` | Generate |
| GET | `/api/v1/admin/reservations` | Reservations |
| GET | `/api/v1/admin/settings` | Settings |
| PATCH | `/api/v1/admin/settings` | Change Settings |
| GET | `/api/v1/admin/users` | Users |
| GET | `/api/v1/admin/users/{identity}` | User |
| PATCH | `/api/v1/admin/users/{identity}/role` | Change Role |
| PATCH | `/api/v1/admin/users/{identity}/status` | Change Status |
| POST | `/api/v1/ai/categorize` | Categorize |
| GET | `/api/v1/ai/category-predictions` | Predictions |
| GET | `/api/v1/ai/category-predictions/{identity}` | Prediction |
| POST | `/api/v1/ai/category-predictions/{identity}/review` | Review |
| POST | `/api/v1/ai/conversations` | Create |
| GET | `/api/v1/ai/conversations` | Listing |
| GET | `/api/v1/ai/conversations/{identity}` | Conversation |
| POST | `/api/v1/ai/conversations/{identity}/messages` | Send |
| POST | `/api/v1/auth/change-password` | Verify current password, change it and revoke all sessions |
| GET | `/api/v1/auth/csrf` | Get a cookie-bound CSRF proof |
| POST | `/api/v1/auth/login` | Authenticate and start a revocable session |
| POST | `/api/v1/auth/logout` | Revoke the current session family and clear its cookie |
| GET | `/api/v1/auth/me` | Get the active authenticated account |
| POST | `/api/v1/auth/refresh` | Rotate the HttpOnly refresh credential; reuse revokes the family |
| POST | `/api/v1/auth/register` | Register an ACTIVE READER; role/status input is forbidden |
| GET | `/api/v1/auth/sessions` | List own active sessions |
| DELETE | `/api/v1/auth/sessions/{session_id}` | Revoke an owned session; other owners' IDs return 404 |
| GET | `/api/v1/authors` | List Authors |
| POST | `/api/v1/authors` | Create Authors |
| GET | `/api/v1/authors/{identity}` | Get Authors |
| PATCH | `/api/v1/authors/{identity}` | Update Authors |
| PATCH | `/api/v1/authors/{identity}/archive` | Archive Authors |
| GET | `/api/v1/books` | Books |
| POST | `/api/v1/books` | Create Book |
| GET | `/api/v1/books/popular` | Popular Books |
| GET | `/api/v1/books/{book_id}` | Book |
| PATCH | `/api/v1/books/{book_id}` | Update Book |
| PATCH | `/api/v1/books/{book_id}/archive` | Archive Book |
| GET | `/api/v1/books/{book_id}/copies` | Copies |
| POST | `/api/v1/books/{book_id}/copies` | Create Copy |
| POST | `/api/v1/books/{book_id}/cover` | Upload Cover |
| DELETE | `/api/v1/books/{book_id}/cover` | Remove Cover |
| GET | `/api/v1/books/{book_id}/similar` | Similar Books |
| POST | `/api/v1/books/{book_id}/views` | Record Book View |
| GET | `/api/v1/borrowings/me/active` | Active |
| GET | `/api/v1/borrowings/me/history` | History |
| GET | `/api/v1/categories` | List Categories |
| POST | `/api/v1/categories` | Create Categories |
| GET | `/api/v1/categories/{identity}` | Get Categories |
| PATCH | `/api/v1/categories/{identity}` | Update Categories |
| PATCH | `/api/v1/categories/{identity}/archive` | Archive Categories |
| PATCH | `/api/v1/copies/{copy_id}` | Update Copy |
| PATCH | `/api/v1/copies/{copy_id}/archive` | Archive Copy |
| GET | `/api/v1/favorites` | Favorites |
| GET | `/api/v1/favorites/{book_id}` | Favorite State |
| POST | `/api/v1/favorites/{book_id}` | Favorite |
| DELETE | `/api/v1/favorites/{book_id}` | Unfavorite |
| GET | `/api/v1/health` | Process liveness |
| POST | `/api/v1/librarian/borrowings` | Direct Issue |
| GET | `/api/v1/librarian/borrowings/by-inventory/{inventory_number}` | Lookup |
| GET | `/api/v1/librarian/borrowings/overdue` | Overdue |
| POST | `/api/v1/librarian/borrowings/{identity}/lost` | Lost Book |
| POST | `/api/v1/librarian/borrowings/{identity}/return` | Return Book |
| GET | `/api/v1/librarian/dashboard` | Dashboard |
| POST | `/api/v1/librarian/qr/verify` | Verify |
| GET | `/api/v1/librarian/readers` | Readers |
| GET | `/api/v1/librarian/readers/{identity}` | Reader |
| GET | `/api/v1/librarian/readers/{identity}/borrowings` | Reader Borrowings |
| GET | `/api/v1/librarian/reservations` | Reservations |
| POST | `/api/v1/librarian/reservations/verify-number` | Manual Verify |
| POST | `/api/v1/librarian/reservations/{identity}/issue` | Issue |
| GET | `/api/v1/media/{filename}` | Media |
| GET | `/api/v1/notifications` | Notifications |
| POST | `/api/v1/notifications/read-all` | Read All |
| PATCH | `/api/v1/notifications/{identity}/read` | Read Notification |
| GET | `/api/v1/publishers` | List Publishers |
| POST | `/api/v1/publishers` | Create Publishers |
| GET | `/api/v1/publishers/{identity}` | Get Publishers |
| PATCH | `/api/v1/publishers/{identity}` | Update Publishers |
| PATCH | `/api/v1/publishers/{identity}/archive` | Archive Publishers |
| GET | `/api/v1/reader/summary` | Summary |
| GET | `/api/v1/ready` | PostgreSQL and Redis readiness |
| POST | `/api/v1/recommendations/impressions` | Record Impression |
| POST | `/api/v1/recommendations/impressions/{identity}/click` | Record Click |
| GET | `/api/v1/recommendations/me` | My Recommendations |
| POST | `/api/v1/reservations` | Reserve |
| GET | `/api/v1/reservations/me` | My Reservations |
| GET | `/api/v1/reservations/{identity}` | Detail |
| POST | `/api/v1/reservations/{identity}/cancel` | Cancel |
| GET | `/api/v1/reservations/{identity}/qr` | Credential |
| GET | `/api/v1/search` | Standard |
| GET | `/api/v1/search/autocomplete` | Suggestions |
| GET | `/api/v1/search/hybrid` | Hybrid |
| GET | `/api/v1/search/semantic` | Semantic |
| POST | `/api/v1/search/{search_id}/click` | Click |
| GET | `/api/v1/users/me` | Profile |
| PATCH | `/api/v1/users/me` | Update Profile |
| POST | `/api/v1/users/me/avatar` | Avatar |
| DELETE | `/api/v1/users/me/avatar` | Remove Avatar |
| GET | `/api/v1/users/me/preferences` | Preferences |
| PATCH | `/api/v1/users/me/preferences` | Update Preferences |
| GET | `/health` | Process liveness |
| GET | `/ready` | PostgreSQL and Redis readiness |

Total: 112 operations on 95 paths.
