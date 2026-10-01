# Recommendations

PHASE 13 implements real popularity, embedding similarity and content-based
personalization. Results are catalog Book objects with current physical-copy
availability; no invented books or digital lending fields exist.

## Algorithms and limits

`RecommendationPolicy` in ai/recommendations/policy.py is the versioned model
configuration. `content-rrf-v1` uses a 90-day activity window: VIEW=1, SEARCH_CLICK
and RECOMMENDATION_CLICK=2, FAVORITE=3, RESERVE=4, BORROW=5. These are transparent
initial model constants, not empirically optimal weights or circulation rules.

Popularity aggregates canonical favorites/reservations/borrowings plus weak
interaction events. Their duplicate FAVORITE/RESERVE/BORROW event rows are excluded
to avoid double-counting the same action. Weak signals count once per UTC day,
Reader, book and type. A cancelled reservation remains evidence of past interest.
Only current favorites created in the window contribute to popularity. Positive
scores are required; zero-activity titles are never labelled popular. Stable
ties use newest catalog creation and UUID. No continuous time decay is active;
the policy/aggregation boundary supports changing the window/decay in a new version.

Similar Books uses pgvector cosine distance in the selected immutable PHASE 12
model space and excludes the source and archived books. Missing source embeddings
produce a truthful empty/pending response, not random substitutes. All copies may
be unavailable without making a bibliographic title disappear.

Personalization combines the Reader's recent canonical actions and weak events,
plus current favorites regardless of age. At most 200 strongest distinct title
signals contribute to the normalized weighted average embedding. Only that bounded
profile transfers vectors to NumPy; candidate ranking/filtering remains in SQL.
All titles previously borrowed by this Reader are excluded from recommendations.
This never blocks manual re-borrowing; an actual repeat loan was tested.

Content rank, positive category-preference rank and positive popularity rank are
combined with the documented RRF baseline `1/(60+rank)` per available signal.
Missing signals contribute zero. These weights are not a measured recommendation
quality claim. Without a usable profile, ranking uses category preferences, then
popularity, then recent titles. Missing local model configuration therefore keeps
personal recommendations usable. Archived categories do not contribute preferences.
User explanations show history/preferences/popularity/recent/similarity, never vectors.

## APIs and UI

- GET `/api/v1/books/popular`: public, positive real activity only.
- GET `/api/v1/books/{book_id}/similar`: public, real embeddings.
- GET `/api/v1/recommendations/me`: active Reader only, identity from authentication.
- POST `/api/v1/recommendations/impressions`: active Reader, signed returned-card receipt.
- POST `/api/v1/recommendations/impressions/{id}/click`: active owner only.

Lists are bounded to 1–20 cards (default popular/personal 8, similar 6). Retrieval
is rate-limited 60/IP/minute; events 180/Reader/minute. Responses are no-store.
Home shows popular books, Book Details shows similar books, Reader dashboard shows
personal recommendations. Kazakh explanations, live copy counts, loading/empty/
pending/error/retry states are included. Relevant mutations invalidate recommendation
queries alongside catalog/search caches.

## Impression and click measurement

Generating or fetching a list creates **no impression**. For authenticated Readers,
the backend returns a 30-minute HMAC receipt binding session family, user, ordered
book IDs, recommendation type, policy version and unique delivery ID. Anonymous
and staff browsing is excluded from this measurement.

The client sends a render signal when at least 50% of a card is visible for one
second in a visible document, or on an explicit card click before that dwell time.
Offscreen/hidden cards do not count. The server validates the receipt, actual
returned book and live session, assigns position/time/source, and deduplicates
delivery/book retries. A click refers to the persisted owned impression and is
deduplicated once per impression. Database FKs bind click/user/book; arbitrary
book IDs, another Reader's receipt/impression and expired/wrong-family receipts fail.

This is client-reported visibility, not proof of human attention. A refreshed
delivery may create a new impression; repeated visibility of the same delivery
does not. Telemetry failure never blocks navigation. Analytics reports CTR only
for this authenticated, attributed population, with numerator and denominator
using the same impression cohort. Anonymous usage is not inferred.

## Collaborative boundary and reproducible evaluation

`CollaborativeRanker` and the working offline `ItemNeighbors` algorithm implement
binary item cosine with minimum two-Reader co-occurrence support. The evaluator
uses actual loans, deduplicates consumed titles and holds out each Reader's last
distinct loan. Its explicit minimum is 20 Readers with at least three distinct
loans and 20 titles; this is a sufficiency guard, not a scientific guarantee.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend python -m app.ai.recommendations.evaluate --output /app/var/models/recommendation-evaluation.json
```

Actual development evaluation found **zero Readers with three distinct loans**;
status INSUFFICIENT_DATA, metrics null, serving disabled. Aggregate evidence is
`ml/evaluation/recommendation_results.json`; it contains no user identifiers.
The content-based system is fully implemented. Collect real interactions or create
explicitly labelled isolated development circulation fixtures, then rerun evaluation.
Before enabling collaborative serving, compare against the content baseline using
a global temporal split and representative data. No collaborative accuracy claimed.

## Verification

PHASE_13_REPORT.md records PostgreSQL, real-vector, component, browser and build
results. Component tests mock the HTTP boundary; database/browser tests exercise
real services and model vectors. No production recommendation mocks exist.


## Optional time decay (PART 153)

Continuous exponential/time-decay weighting is not active. The versioned policy
already bounds popularity to a 90-day window and keeps scoring separate from
retrieval, so an explicitly evaluated decay function can be added without changing
circulation or stored events. No continuous decay behavior is claimed.
