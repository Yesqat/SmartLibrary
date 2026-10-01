# AI and ML architecture

Status: PHASE 12 implements real multilingual embeddings and semantic/hybrid search.
The E5 small/base comparison selected pinned E5 base (768 dimensions); actual
metrics, limitations, generation and recovery are in [SEMANTIC_SEARCH.md](SEMANTIC_SEARCH.md).
PHASE 13 implements popular/similar/personal recommendations and rendered-card
attribution; see RECOMMENDATIONS.md. PHASE 14 implements both categorization methods,
held-out evaluation and transactional human review; see CATEGORIZATION.md for
the small-dataset limitations and measured results. PHASE 15 implements controlled
LLM orchestration, owned conversations and safe outage behavior; see AI_ASSISTANT.md.
Live external-provider credentials/quality remain unverified. Collaborative serving is disabled after actual data-sufficiency
evaluation found zero Readers with three distinct loans; no accuracy is fabricated.
Sources: PARTS 54–84, 123–126, 150–155, 175, 185–188.

The default worker consumes only the default queue. PHASE 12 adds a dedicated ML
consumer and Beat's recoverable missing-vector sweep. Actual pinned local inference
is used; no fake embeddings or external LLM responses exist.

## Local search and recommendation

sentence-transformers generates multilingual vectors from stable title/description/author/category metadata. Benchmark Kazakh, Russian and English on a versioned dataset before selecting a model, dimension and threshold. Persist model name/revision, source hash and generation time. Re-embed on relevant edits; stale jobs must not overwrite newer source versions. Use dedicated queues for expensive local ML so reminders and expiration remain responsive.

PostgreSQL pgvector stores and queries vectors; pg_trgm and lexical queries provide standard/fuzzy retrieval. Model changes require a separately versioned vector space and migration/re-embedding plan. Never compare vectors from incompatible models, even with equal dimensions.

PHASE 2 implements immutable `embedding_models` provenance and `book_embeddings`
with model/dimension foreign keys, per-vector dimension checks and unique
book/model pairs. The pgvector column accepts versioned spaces of different
dimensions while each row must match its model. PHASE 12 selected the model through
the multilingual benchmark. Exact pgvector scanning with the model B-tree index
is measured on the current small corpus; an approximate index is not yet justified.

Hybrid search fuses SQL lexical/vector ranks using published RRF k=60, with filters
applied before ranking and exact ISBN/title priority. Current relational copy
availability remains authoritative. No model accuracy beyond measured examples is claimed.

Recommendation uses real weighted interactions, favorites, reservations, borrowings and optional category preferences. Popularity uses the documented versioned 90-day event policy in RECOMMENDATIONS.md. Similar books use vectors and exclude the source book. Personalized profiles use weighted embeddings with category/popularity signals and read-book down-ranking. New users receive category/popular/recent fallbacks. These ranking exclusions never prohibit a legitimate repeat loan.

Keep a collaborative-signal service boundary and reproducible seed/evaluation pathway. Implement meaningful collaborative filtering when data supports it; insufficient data is a documented limitation, not permission to fabricate effectiveness. Time decay remains an optional documented extension unless implemented and tested.

## Categorization

Multi-label predictions are restricted to existing database categories. Build TF-IDF plus One-vs-Rest Logistic Regression baseline and embedding-based category similarity, with reproducible disjoint training/validation/test data when dataset size permits. Select thresholds on validation data; evaluate held-out precision/recall/micro and macro F1 and per-category metrics. Record dataset/version/split seed, model/configuration and limitations. Similarity is not automatically a calibrated probability.

Staff explicitly accepts, rejects or modifies predictions before saving final book categories. Store review state and model provenance. Acceptance rate uses reviewed predictions and is operational feedback, not model accuracy. Metadata/category edits invalidate the relevant book embeddings.

The schema stores prediction runs, individual scores with explicit score kinds,
nullable unreviewed outcomes and the final reviewed category set, including
manual additions. Conversation ownership, message usage/error metadata and
foreign-key-backed message/book references are implemented. The seed inserts
no synthetic prediction, embedding, assistant response or recommendation
impression. Small numeric vectors in isolated tests exercise database operators
only; they are not model-quality evidence.

## Assistant

Use a provider-configurable LLMClient, bounded conversation context, explicit timeouts and validated tool outputs. Tool allowlist: search_books, semantic_search_books, get_book_details, check_book_availability, get_similar_books, get_recommendations, get_my_borrowings, get_my_reservations, get_library_rules.

Personal tools derive user identity exclusively from backend authentication. The model cannot select arbitrary users, run SQL, issue/return books or silently reserve. A Reserve button requires explicit user confirmation through the normal reservation endpoint. Tool inputs, retrieved descriptions and model output are untrusted. Enforce allowlists, parameter schemas and bounded tool execution independently of prompts.

Every library fact comes from current backend data. Validate returned book references against actual results. Do not reuse conversation availability/due dates as current facts. Minimize context and never send secrets, password hashes or unrelated private records.

LLM configuration requires LLM_PROVIDER, LLM_MODEL and LLM_API_KEY. Their absence must produce a controlled assistant unavailable state while core circulation, standard search and administration continue. Local semantic/recommendation availability depends on local models, not the external LLM. No external credential is required for core library workflows or local ML.

## Telemetry and reproducibility

Record actual search events, assistant usage/failure timing, prediction reviews and recommendation sources. Track deduplicated rendered impressions before reporting CTR. Store evaluation artifacts separately from live operational metrics. No fake accuracy, uptime, recommendation relevance or availability claims.
