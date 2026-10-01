# Standard and fuzzy search

PHASE 5 uses PostgreSQL queries against real catalog/circulation records.
PHASE 12 adds real Semantic and Hybrid Search; see [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md).

## Endpoints and filters

`GET /api/v1/search` accepts q (up to 500 characters), category/author/publisher
UUIDs, repeated language codes, year_from/year_to, available, sort, page and
page_size. All filters combine with AND. Within language, any selected code
matches. Reversed year ranges, invalid identifiers/sorts, unknown query fields
and unbounded page sizes fail with the standard safe 422 response. Page size
defaults to 20, maximum 100. `available=false` means no active available copy.
Archived titles are excluded; include_archived requires catalog permission.

Responses extend the catalog page with nullable search_event_id and indexing_pending.
The mode parameter selects standard (default), semantic or hybrid. Book DTOs keep
current physical availability. Public GET author/category/publisher by UUID
supports restoring filter labels from bookmarked URLs without downloading whole
reference tables. Search and autocomplete do not require login.

## Ranking and sort definitions

Default relevance uses ordered tiers, not an unexplained weighted score:

1. Exact normalized ISBN (spaces/hyphens ignored).
2. Exact case-insensitive title.
3. Title prefix.
4. Title containment.
5. Author containment.
6. Category containment.
7. Publisher containment.
8. Description containment.
9. Trigram title/author match.

Within a tier, title trigram similarity descends, then lowercase title and UUID
provide deterministic ordering. All containment/prefix input escapes SQL wildcard
characters. SQLAlchemy binds values. Queries never interpolate request SQL.
pg_trgm `%` is used for fuzzy candidates when q has at least three characters;
the documented PostgreSQL default similarity cutoff 0.3 is explicitly SET LOCAL
per retrieval. It does not leak across pooled transactions. This is a practical
baseline, not a measured universal linguistic optimum. Tested examples include
`Clen Code` → `Clean Code` and `Абай жоли` → `Абай жолы`.

Supported sorts: relevance, popularity, recent, year_desc, year_asc, title_asc,
title_desc. Exact ISBN/title matches remain pinned first across these sorts.
Popularity currently means lifetime count of actual borrowing rows for a title,
including completed loans. It does not invent popularity for new books or count
every view as a loan. PHASE 13 will add the documented recommendation model.
Unknown publication years sort last in either direction. Stable UUID tie-breaks
prevent unstable page ordering when other values are equal.

## Autocomplete and frontend

GET `/api/v1/search/autocomplete?q=...&limit=...` returns a combined bounded list
of books and authors (default eight, maximum ten). Queries shorter than two
characters return no suggestions. Exact/prefix/containment precede fuzzy matches.
Archived books/authors are excluded; an author must have an active catalog title.
The browser debounces input by 250 ms and aborts stale transport requests.
Book suggestions navigate to details; author suggestions navigate to an actual
search context. Suggestions are not a client-side copy of the full catalog.

Public `/catalog` provides query, combined filters, real result count, sort and
pagination. URL state survives reloads/bookmarks. Filter-reference labels are
resolved from real APIs. States include loading, empty, failure/retry and bounded
suggestions. Existing staff catalog editing remains available. Home search leads
to the public catalog. Cards show language/year/category and live availability.

## Event semantics and security

A nonempty q produces one immutable search_events row per successfully executed
search API request, including pagination and explicit refetch/retry requests.
These are search executions, **not unique user search sessions**. Empty-q browsing
and autocomplete are excluded. Zero-result executions are included. Filters store
sort/page and the bounded result UUIDs actually returned, supporting honest click
attribution. Identity is authenticated user or NULL for an anonymous request.

POST `/api/v1/search/{search_event_id}/click` accepts book_id and a client event
UUID. It requires an active Reader, bearer authentication and allowed Origin.
The event must belong to that Reader and its stored results must contain the book.
An authenticated user cannot attribute a click to another Reader's or anonymous
search. The user/event key deduplicates retries. Click records use SEARCH_CLICK /
the corresponding STANDARD_SEARCH/SEMANTIC_SEARCH/HYBRID_SEARCH source and actual
search event FK. Failure to record analytics never
blocks navigation. A detail visit also records the separate VIEW signal.

Redis limits: search 120/IP/minute, autocomplete 180/IP/minute, click 120/user/minute.
Keys use existing HMAC identity protection. Rate limits return 429/Retry-After;
an unavailable limiter returns safe SEARCH_FAILED/503. No queries or private
credentials are added to request logs. Standard search has no AI dependency;
semantic/hybrid use local models and have no external LLM dependency.

## Query verification and limitations

SQL applies filtering/counting/sorting/pagination. EXISTS subqueries avoid duplicate
books when authors/categories multiply. Availability is one grouped relation,
with select-in loading of authors/categories. A retrieval uses five queries
including SET LOCAL; event persistence adds one INSERT. No full catalog is loaded
into Python or the browser. Existing ISBN, trigram, relation, year/language and
copy-allocation indexes remain synchronized with the three original migrations.

Actual EXPLAIN ANALYZE/BUFFERS plans are saved in
`work/logs/phase5-query-plans.jsonl`. On the small development fixture, available
Kazakh query `Абай` returned two rows in about 2.63 ms execution / 16.22 ms planning;
`Clen Code` with availability filter returned zero rows in about 0.64 / 3.02 ms
(the seeded matching title has no available copies). These are single diagnostic
measurements, not load-test or production-latency claims. Small-table scans are
expected; no claim is made that every plan uses a trigram index. PostgreSQL tests
separately verify that the unfiltered typo query returns Clean Code.
