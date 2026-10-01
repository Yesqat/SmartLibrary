# Core schema reference

Generated from SQLAlchemy models by scripts/export_schema_reference.py. Live verification results belong in PHASE_2_REPORT.md. All entity keys are UUIDs; timestamps use timestamptz. The acquired_at physical-copy field is a calendar date.

## Enum types

- **borrowing_status**: BORROWED, RETURNED, OVERDUE, LOST
- **copy_condition**: NEW, GOOD, FAIR, POOR, DAMAGED
- **copy_status**: AVAILABLE, RESERVED, BORROWED, DAMAGED, LOST, MAINTENANCE
- **interaction_source**: CATALOG, STANDARD_SEARCH, SEMANTIC_SEARCH, HYBRID_SEARCH, RECOMMENDATION, AI_ASSISTANT, SIMILAR_BOOKS, POPULAR_BOOKS
- **interaction_type**: VIEW, SEARCH_CLICK, FAVORITE, RESERVE, BORROW, RECOMMENDATION_CLICK
- **message_role**: USER, ASSISTANT
- **notification_type**: RESERVATION_READY, RESERVATION_EXPIRING, RESERVATION_EXPIRED, DUE_SOON, OVERDUE
- **prediction_review**: PENDING, ACCEPTED, MODIFIED, REJECTED
- **recommendation_type**: PERSONALIZED, SIMILAR_BOOK, POPULAR
- **related_entity**: RESERVATION, BORROWING, BOOK
- **reservation_status**: WAITING, READY, COMPLETED, CANCELLED, EXPIRED
- **score_kind**: PROBABILITY, COSINE_SIMILARITY, DECISION_FUNCTION
- **search_type**: STANDARD, SEMANTIC, HYBRID
- **setting_type**: INTEGER, BOOLEAN, STRING, JSON
- **user_role**: READER, LIBRARIAN, ADMIN
- **user_status**: ACTIVE, BLOCKED, INACTIVE

## authors

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| full_name | VARCHAR(300) | no |  |
| biography | TEXT | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |
| archived_at | TIMESTAMP WITH TIME ZONE | yes |  |

Constraints:

- `pk_authors`: PRIMARY KEY (id).
- `ck_authors_name`: CHECK `length(btrim(full_name)) > 0`.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_authors_name_trgm ON authors USING gin (full_name gin_trgm_ops);
```

## categories

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| name | VARCHAR(150) | no |  |
| description | TEXT | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |
| archived_at | TIMESTAMP WITH TIME ZONE | yes |  |

Constraints:

- `pk_categories`: PRIMARY KEY (id).
- `ck_categories_name`: CHECK `length(btrim(name)) > 0`.
- `uq_categories_name`: UNIQUE (name).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_categories_name_trgm ON categories USING gin (name gin_trgm_ops);
```

## embedding_models

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| model_name | VARCHAR(250) | no |  |
| revision | VARCHAR(150) | no |  |
| dimension | INTEGER | no |  |
| source_recipe | VARCHAR(100) | no |  |
| normalized | BOOLEAN | no | true |
| configuration | JSONB | no | '{}'::jsonb |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_embedding_models`: PRIMARY KEY (id).
- `ck_embedding_models_configuration`: CHECK `jsonb_typeof(configuration) = 'object'`.
- `ck_embedding_models_dimension`: CHECK `dimension BETWEEN 1 AND 16000`.
- `ck_embedding_models_provenance`: CHECK `length(btrim(model_name)) > 0 AND length(btrim(revision)) > 0 AND length(btrim(source_recipe)) > 0`.
- `uq_embedding_models_dimension`: UNIQUE (id, dimension).
- `uq_embedding_models_space`: UNIQUE (model_name, revision, source_recipe).

## publishers

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| name | VARCHAR(250) | no |  |
| country | VARCHAR(100) | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |
| archived_at | TIMESTAMP WITH TIME ZONE | yes |  |

Constraints:

- `pk_publishers`: PRIMARY KEY (id).
- `ck_publishers_name`: CHECK `length(btrim(name)) > 0`.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_publishers_name_trgm ON publishers USING gin (name gin_trgm_ops);
```

## users

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| first_name | VARCHAR(100) | no |  |
| last_name | VARCHAR(100) | no |  |
| email | VARCHAR(320) | no |  |
| password_hash | TEXT | no |  |
| phone | VARCHAR(32) | yes |  |
| avatar_url | TEXT | yes |  |
| role | user_role | no | READER |
| status | user_status | no | ACTIVE |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_users`: PRIMARY KEY (id).
- `ck_users_email`: CHECK `email = lower(btrim(email)) AND position('@' in email) > 1`.
- `ck_users_names`: CHECK `length(btrim(first_name)) > 0 AND length(btrim(last_name)) > 0`.
- `ck_users_password_algorithm`: CHECK `password_hash LIKE '$argon2id$%'`.
- `uq_users_email`: UNIQUE (email).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_users_name ON users (last_name, first_name);
CREATE INDEX ix_users_role_status_created ON users (role, status, created_at);
CREATE INDEX ix_users_status ON users (status);
```

## ai_conversations

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| title | VARCHAR(300) | yes |  |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_ai_conversations`: PRIMARY KEY (id).
- `fk_ai_conversations_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_ai_conversations_user_updated ON ai_conversations (user_id, updated_at);
```

## audit_logs

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | yes |  |
| action | VARCHAR(100) | no |  |
| entity_type | VARCHAR(100) | no |  |
| entity_id | UUID | yes |  |
| details | JSONB | yes |  |
| ip_address | INET | yes |  |
| request_id | UUID | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_audit_logs`: PRIMARY KEY (id).
- `fk_audit_logs_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_audit_logs_action`: CHECK `action ~ '^[A-Z][A-Z0-9_]+$'`.
- `ck_audit_logs_details_object`: CHECK `details IS NULL OR jsonb_typeof(details) = 'object'`.
- `ck_audit_logs_entity_type`: CHECK `length(btrim(entity_type)) > 0`.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_audit_logs_action_time ON audit_logs (action, created_at);
CREATE INDEX ix_audit_logs_actor_time ON audit_logs (user_id, created_at);
CREATE INDEX ix_audit_logs_entity_time ON audit_logs (entity_type, entity_id, created_at);
CREATE INDEX ix_audit_logs_time ON audit_logs (created_at, id);
```

## books

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| title | VARCHAR(500) | no |  |
| isbn | VARCHAR(13) | yes |  |
| description | TEXT | yes |  |
| publication_year | INTEGER | yes |  |
| publisher_id | UUID | yes |  |
| language | VARCHAR(35) | no |  |
| page_count | INTEGER | yes |  |
| cover_url | TEXT | yes |  |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |
| archived_at | TIMESTAMP WITH TIME ZONE | yes |  |

Constraints:

- `pk_books`: PRIMARY KEY (id).
- `fk_books_publisher_id_publishers`: (publisher_id) → (publishers.id), DELETE RESTRICT.
- `ck_books_isbn`: CHECK `isbn IS NULL OR isbn ~ '^([0-9]{13}|[0-9]{9}[0-9X])$'`.
- `ck_books_language`: CHECK `language ~ '^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$'`.
- `ck_books_page_count`: CHECK `page_count IS NULL OR page_count > 0`.
- `ck_books_publication_year`: CHECK `publication_year IS NULL OR publication_year BETWEEN 1 AND 9999`.
- `ck_books_title`: CHECK `length(btrim(title)) > 0`.
- `uq_books_isbn`: UNIQUE (isbn).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_books_created ON books (created_at, id);
CREATE INDEX ix_books_description_trgm ON books USING gin (description gin_trgm_ops);
CREATE INDEX ix_books_language_year ON books (language, publication_year);
CREATE INDEX ix_books_publication_year ON books (publication_year);
CREATE INDEX ix_books_publisher_id ON books (publisher_id);
CREATE INDEX ix_books_title ON books (title);
CREATE INDEX ix_books_title_trgm ON books USING gin (title gin_trgm_ops);
```

## refresh_sessions

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| family_id | UUID | no |  |
| parent_id | UUID | yes |  |
| token_hash | VARCHAR(64) | no |  |
| expires_at | TIMESTAMP WITH TIME ZONE | no |  |
| consumed_at | TIMESTAMP WITH TIME ZONE | yes |  |
| revoked_at | TIMESTAMP WITH TIME ZONE | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_refresh_sessions`: PRIMARY KEY (id).
- `fk_refresh_sessions_parent_family`: (parent_id, user_id, family_id) → (refresh_sessions.id, refresh_sessions.user_id, refresh_sessions.family_id), DELETE RESTRICT.
- `fk_refresh_sessions_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_refresh_sessions_consumption`: CHECK `consumed_at IS NULL OR consumed_at >= created_at`.
- `ck_refresh_sessions_expiry`: CHECK `expires_at > created_at`.
- `ck_refresh_sessions_no_self_parent`: CHECK `parent_id IS NULL OR parent_id <> id`.
- `ck_refresh_sessions_revocation`: CHECK `revoked_at IS NULL OR revoked_at >= created_at`.
- `ck_refresh_sessions_token_hash`: CHECK `token_hash ~ '^[0-9a-f]{64}$'`.
- `uq_refresh_sessions_identity_family`: UNIQUE (id, user_id, family_id).
- `uq_refresh_sessions_parent_id`: UNIQUE (parent_id).
- `uq_refresh_sessions_token_hash`: UNIQUE (token_hash).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_refresh_sessions_expiry ON refresh_sessions (expires_at);
CREATE INDEX ix_refresh_sessions_user_family ON refresh_sessions (user_id, family_id);
```

## search_events

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | yes |  |
| query | VARCHAR(2000) | no |  |
| search_type | search_type | no |  |
| result_count | INTEGER | no |  |
| filters | JSONB | no | '{}'::jsonb |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_search_events`: PRIMARY KEY (id).
- `fk_search_events_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_search_events_filters_object`: CHECK `jsonb_typeof(filters) = 'object'`.
- `ck_search_events_query`: CHECK `length(btrim(query)) > 0`.
- `ck_search_events_result_count`: CHECK `result_count >= 0`.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_search_events_time ON search_events (created_at);
CREATE INDEX ix_search_events_type_time ON search_events (search_type, created_at);
CREATE INDEX ix_search_events_user_id ON search_events (user_id);
CREATE INDEX ix_search_events_zero_results ON search_events (created_at) WHERE result_count = 0;
```

## system_settings

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| key | VARCHAR(100) | no |  |
| value | JSONB | no |  |
| value_type | setting_type | no |  |
| minimum | NUMERIC | yes |  |
| maximum | NUMERIC | yes |  |
| description | TEXT | no |  |
| updated_by | UUID | yes |  |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_system_settings`: PRIMARY KEY (id).
- `fk_system_settings_updated_by_users`: (updated_by) → (users.id), DELETE RESTRICT.
- `ck_system_settings_bounds`: CHECK `minimum IS NULL OR maximum IS NULL OR minimum <= maximum`.
- `ck_system_settings_key`: CHECK `key ~ '^[a-z][a-z0-9_]+$'`.
- `ck_system_settings_typed_value`: CHECK `CASE value_type WHEN 'INTEGER' THEN CASE WHEN jsonb_typeof(value) = 'number' THEN (value::text)::numeric = trunc((value::text)::numeric) AND (minimum IS NULL OR (value::text)::numeric >= minimum) AND (maximum IS NULL OR (value::text)::numeric <= maximum) ELSE false END WHEN 'BOOLEAN' THEN jsonb_typeof(value) = 'boolean' WHEN 'STRING' THEN jsonb_typeof(value) = 'string' WHEN 'JSON' THEN jsonb_typeof(value) IN ('object','array') END`.
- `uq_system_settings_key`: UNIQUE (key).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_system_settings_updated_by ON system_settings (updated_by);
```

## user_category_preferences

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| category_id | UUID | no |  |
| weight | NUMERIC(8, 4) | no | 1 |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_user_category_preferences`: PRIMARY KEY (id).
- `fk_user_category_preferences_category_id_categories`: (category_id) → (categories.id), DELETE RESTRICT.
- `fk_user_category_preferences_user_id_users`: (user_id) → (users.id), DELETE CASCADE.
- `ck_user_category_preferences_weight`: CHECK `weight >= 0 AND weight < 'Infinity'::numeric`.
- `uq_user_category_preferences_user_id`: UNIQUE (user_id, category_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_user_category_preferences_category_id ON user_category_preferences (category_id);
```

## ai_messages

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| conversation_id | UUID | no |  |
| role | message_role | no |  |
| content | TEXT | no |  |
| tool_metadata | JSONB | no | '{}'::jsonb |
| model_name | VARCHAR(250) | yes |  |
| latency_ms | INTEGER | yes |  |
| input_tokens | INTEGER | yes |  |
| output_tokens | INTEGER | yes |  |
| error_code | VARCHAR(100) | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_ai_messages`: PRIMARY KEY (id).
- `fk_ai_messages_conversation_id_ai_conversations`: (conversation_id) → (ai_conversations.id), DELETE CASCADE.
- `ck_ai_messages_content`: CHECK `length(btrim(content)) > 0`.
- `ck_ai_messages_input_tokens`: CHECK `input_tokens IS NULL OR input_tokens >= 0`.
- `ck_ai_messages_latency`: CHECK `latency_ms IS NULL OR latency_ms >= 0`.
- `ck_ai_messages_output_tokens`: CHECK `output_tokens IS NULL OR output_tokens >= 0`.
- `ck_ai_messages_tool_metadata`: CHECK `jsonb_typeof(tool_metadata) = 'object'`.

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_ai_messages_conversation_time ON ai_messages (conversation_id, created_at, id);
CREATE INDEX ix_ai_messages_role_time ON ai_messages (role, created_at);
```

## book_authors

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| book_id | UUID | no |  |
| author_id | UUID | no |  |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_book_authors`: PRIMARY KEY (id).
- `fk_book_authors_author_id_authors`: (author_id) → (authors.id), DELETE RESTRICT.
- `fk_book_authors_book_id_books`: (book_id) → (books.id), DELETE CASCADE.
- `uq_book_authors_book_id`: UNIQUE (book_id, author_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_book_authors_author_id ON book_authors (author_id);
```

## book_categories

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| book_id | UUID | no |  |
| category_id | UUID | no |  |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_book_categories`: PRIMARY KEY (id).
- `fk_book_categories_book_id_books`: (book_id) → (books.id), DELETE CASCADE.
- `fk_book_categories_category_id_categories`: (category_id) → (categories.id), DELETE RESTRICT.
- `uq_book_categories_book_id`: UNIQUE (book_id, category_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_book_categories_category_id ON book_categories (category_id);
```

## book_copies

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| book_id | UUID | no |  |
| inventory_number | VARCHAR(100) | no |  |
| shelf_location | VARCHAR(150) | yes |  |
| status | copy_status | no | AVAILABLE |
| condition | copy_condition | no | GOOD |
| acquired_at | DATE | yes |  |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |
| archived_at | TIMESTAMP WITH TIME ZONE | yes |  |

Constraints:

- `pk_book_copies`: PRIMARY KEY (id).
- `fk_book_copies_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `ck_book_copies_archive_not_circulating`: CHECK `archived_at IS NULL OR status NOT IN ('RESERVED','BORROWED')`.
- `ck_book_copies_damaged_not_circulating`: CHECK `condition <> 'DAMAGED' OR status IN ('DAMAGED','MAINTENANCE','LOST')`.
- `ck_book_copies_inventory_number`: CHECK `length(btrim(inventory_number)) > 0`.
- `uq_book_copies_identity_book`: UNIQUE (id, book_id).
- `uq_book_copies_inventory_number`: UNIQUE (inventory_number).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_book_copies_allocation ON book_copies (book_id, status, acquired_at, created_at, id);
CREATE INDEX ix_book_copies_status ON book_copies (status);
```

## book_embeddings

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| book_id | UUID | no |  |
| model_id | UUID | no |  |
| dimension | INTEGER | no |  |
| embedding | VECTOR | no |  |
| source_hash | VARCHAR(64) | no |  |
| generated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_book_embeddings`: PRIMARY KEY (id).
- `fk_book_embeddings_book_id_books`: (book_id) → (books.id), DELETE CASCADE.
- `fk_book_embeddings_model_dimension`: (model_id, dimension) → (embedding_models.id, embedding_models.dimension), DELETE RESTRICT.
- `ck_book_embeddings_dimension`: CHECK `vector_dims(embedding) = dimension`.
- `ck_book_embeddings_nonzero_vector`: CHECK `vector_norm(embedding) > 0`.
- `ck_book_embeddings_source_hash`: CHECK `source_hash ~ '^[0-9a-f]{64}$'`.
- `uq_book_embeddings_book_id`: UNIQUE (book_id, model_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_book_embeddings_model ON book_embeddings (model_id, book_id);
```

## category_prediction_runs

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| book_id | UUID | no |  |
| requested_by | UUID | no |  |
| model_name | VARCHAR(250) | no |  |
| model_revision | VARCHAR(150) | no |  |
| source_hash | VARCHAR(64) | no |  |
| configuration | JSONB | no | '{}'::jsonb |
| review_status | prediction_review | no | PENDING |
| reviewed_by | UUID | yes |  |
| reviewed_at | TIMESTAMP WITH TIME ZONE | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_category_prediction_runs`: PRIMARY KEY (id).
- `fk_category_prediction_runs_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_category_prediction_runs_requested_by_users`: (requested_by) → (users.id), DELETE RESTRICT.
- `fk_category_prediction_runs_reviewed_by_users`: (reviewed_by) → (users.id), DELETE RESTRICT.
- `ck_category_prediction_runs_configuration`: CHECK `jsonb_typeof(configuration) = 'object'`.
- `ck_category_prediction_runs_review`: CHECK `(review_status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (review_status <> 'PENDING' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND reviewed_at >= created_at)`.
- `ck_category_prediction_runs_source_hash`: CHECK `source_hash ~ '^[0-9a-f]{64}$'`.
- `uq_category_prediction_runs_identity_book`: UNIQUE (id, book_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_category_prediction_runs_book_id ON category_prediction_runs (book_id);
CREATE INDEX ix_category_prediction_runs_created ON category_prediction_runs (created_at);
CREATE INDEX ix_category_prediction_runs_requested_by ON category_prediction_runs (requested_by);
CREATE INDEX ix_category_prediction_runs_review_time ON category_prediction_runs (review_status, created_at);
CREATE INDEX ix_category_prediction_runs_reviewed ON category_prediction_runs (reviewed_at) WHERE reviewed_at IS NOT NULL;
CREATE INDEX ix_category_prediction_runs_reviewed_by ON category_prediction_runs (reviewed_by);
```

## favorites

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| book_id | UUID | no |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_favorites`: PRIMARY KEY (id).
- `fk_favorites_book_id_books`: (book_id) → (books.id), DELETE CASCADE.
- `fk_favorites_user_id_users`: (user_id) → (users.id), DELETE CASCADE.
- `uq_favorites_user_id`: UNIQUE (user_id, book_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_favorites_book_id ON favorites (book_id);
```

## recommendation_impressions

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| book_id | UUID | no |  |
| recommendation_type | recommendation_type | no |  |
| source | interaction_source | no |  |
| shown_at | TIMESTAMP WITH TIME ZONE | no |  |
| position | INTEGER | no |  |
| event_key | VARCHAR(150) | no |  |
| model_name | VARCHAR(250) | yes |  |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_recommendation_impressions`: PRIMARY KEY (id).
- `fk_recommendation_impressions_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_recommendation_impressions_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_recommendation_impressions_event_key`: CHECK `length(btrim(event_key)) > 0`.
- `ck_recommendation_impressions_position`: CHECK `position >= 1`.
- `uq_recommendation_impressions_event_key`: UNIQUE (event_key).
- `uq_recommendation_impressions_identity`: UNIQUE (id, user_id, book_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_recommendation_impressions_book_id ON recommendation_impressions (book_id);
CREATE INDEX ix_recommendation_impressions_time ON recommendation_impressions (shown_at);
CREATE INDEX ix_recommendation_impressions_type_time ON recommendation_impressions (recommendation_type, shown_at);
CREATE INDEX ix_recommendation_impressions_user_time ON recommendation_impressions (user_id, shown_at);
```

## ai_message_books

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| message_id | UUID | no |  |
| book_id | UUID | no |  |
| position | INTEGER | no |  |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_ai_message_books`: PRIMARY KEY (id).
- `fk_ai_message_books_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_ai_message_books_message_id_ai_messages`: (message_id) → (ai_messages.id), DELETE CASCADE.
- `ck_ai_message_books_position`: CHECK `position >= 1`.
- `uq_ai_message_books_message_id`: UNIQUE (message_id, book_id).
- `uq_ai_message_books_position`: UNIQUE (message_id, position).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_ai_message_books_book_id ON ai_message_books (book_id);
```

## category_prediction_selections

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| run_id | UUID | no |  |
| category_id | UUID | no |  |
| id | UUID | no | gen_random_uuid() |

Constraints:

- `pk_category_prediction_selections`: PRIMARY KEY (id).
- `fk_category_prediction_selections_category_id_categories`: (category_id) → (categories.id), DELETE RESTRICT.
- `fk_category_prediction_selections_run_id_category_predi_5932`: (run_id) → (category_prediction_runs.id), DELETE RESTRICT.
- `uq_category_prediction_selections_run_id`: UNIQUE (run_id, category_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_category_prediction_selections_category_id ON category_prediction_selections (category_id);
```

## category_predictions

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| run_id | UUID | no |  |
| book_id | UUID | no |  |
| category_id | UUID | no |  |
| confidence | FLOAT | no |  |
| score_kind | score_kind | no |  |
| accepted | BOOLEAN | yes |  |
| reviewed_by | UUID | yes |  |
| reviewed_at | TIMESTAMP WITH TIME ZONE | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_category_predictions`: PRIMARY KEY (id).
- `fk_category_predictions_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_category_predictions_category_id_categories`: (category_id) → (categories.id), DELETE RESTRICT.
- `fk_category_predictions_reviewed_by_users`: (reviewed_by) → (users.id), DELETE RESTRICT.
- `fk_category_predictions_run_book`: (run_id, book_id) → (category_prediction_runs.id, category_prediction_runs.book_id), DELETE RESTRICT.
- `ck_category_predictions_review`: CHECK `(accepted IS NULL AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (accepted IS NOT NULL AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND reviewed_at >= created_at)`.
- `ck_category_predictions_score`: CHECK `confidence > '-Infinity'::float8 AND confidence < 'Infinity'::float8 AND (score_kind = 'DECISION_FUNCTION' OR (score_kind = 'PROBABILITY' AND confidence BETWEEN 0 AND 1) OR (score_kind = 'COSINE_SIMILARITY' AND confidence BETWEEN -1 AND 1))`.
- `uq_category_predictions_run_id`: UNIQUE (run_id, category_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_category_predictions_book_id ON category_predictions (book_id);
CREATE INDEX ix_category_predictions_category_id ON category_predictions (category_id);
CREATE INDEX ix_category_predictions_created ON category_predictions (created_at);
CREATE INDEX ix_category_predictions_review_time ON category_predictions (accepted, created_at);
CREATE INDEX ix_category_predictions_reviewed ON category_predictions (reviewed_at) WHERE reviewed_at IS NOT NULL;
CREATE INDEX ix_category_predictions_reviewed_by ON category_predictions (reviewed_by);
```

## reservations

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| reservation_number | VARCHAR(64) | no | 'R-' &#124;&#124; nextval('reservation_number_seq')::text |
| user_id | UUID | no |  |
| book_id | UUID | no |  |
| book_copy_id | UUID | yes |  |
| qr_token_hash | VARCHAR(64) | yes |  |
| qr_token_ciphertext | TEXT | yes |  |
| qr_key_id | VARCHAR(50) | yes |  |
| reserved_at | TIMESTAMP WITH TIME ZONE | no | now() |
| ready_at | TIMESTAMP WITH TIME ZONE | yes |  |
| expires_at | TIMESTAMP WITH TIME ZONE | yes |  |
| completed_at | TIMESTAMP WITH TIME ZONE | yes |  |
| cancelled_at | TIMESTAMP WITH TIME ZONE | yes |  |
| status | reservation_status | no | WAITING |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_reservations`: PRIMARY KEY (id).
- `fk_reservations_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_reservations_copy_book`: (book_copy_id, book_id) → (book_copies.id, book_copies.book_id), DELETE RESTRICT.
- `fk_reservations_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_reservations_cancelled_date`: CHECK `cancelled_at IS NULL OR cancelled_at >= reserved_at`.
- `ck_reservations_completed_date`: CHECK `completed_at IS NULL OR completed_at >= ready_at`.
- `ck_reservations_hold_dates`: CHECK `(ready_at IS NULL AND book_copy_id IS NULL AND expires_at IS NULL) OR (ready_at IS NOT NULL AND book_copy_id IS NOT NULL AND expires_at IS NOT NULL AND ready_at >= reserved_at AND expires_at > ready_at)`.
- `ck_reservations_number`: CHECK `length(btrim(reservation_number)) > 0`.
- `ck_reservations_qr_hash`: CHECK `qr_token_hash IS NULL OR qr_token_hash ~ '^[0-9a-f]{64}$'`.
- `ck_reservations_qr_lifecycle`: CHECK `(status = 'READY' AND qr_token_hash IS NOT NULL AND qr_token_ciphertext IS NOT NULL AND qr_key_id IS NOT NULL) OR (status <> 'READY' AND qr_token_hash IS NULL AND qr_token_ciphertext IS NULL AND qr_key_id IS NULL)`.
- `ck_reservations_state_fields`: CHECK `(status = 'WAITING' AND book_copy_id IS NULL AND ready_at IS NULL AND expires_at IS NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR (status = 'READY' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL AND expires_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR (status = 'COMPLETED' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL AND expires_at IS NOT NULL AND completed_at IS NOT NULL AND cancelled_at IS NULL) OR (status = 'CANCELLED' AND cancelled_at IS NOT NULL AND completed_at IS NULL) OR (status = 'EXPIRED' AND book_copy_id IS NOT NULL AND ready_at IS NOT NULL AND expires_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL)`.
- `uq_reservations_identity_assignment`: UNIQUE (id, user_id, book_copy_id).
- `uq_reservations_identity_user`: UNIQUE (id, user_id).
- `uq_reservations_qr_token_hash`: UNIQUE (qr_token_hash).
- `uq_reservations_reservation_number`: UNIQUE (reservation_number).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_reservations_book_status ON reservations (book_id, status);
CREATE INDEX ix_reservations_cancelled_time ON reservations (cancelled_at) WHERE cancelled_at IS NOT NULL;
CREATE INDEX ix_reservations_completed_time ON reservations (completed_at) WHERE completed_at IS NOT NULL;
CREATE INDEX ix_reservations_copy ON reservations (book_copy_id);
CREATE INDEX ix_reservations_expired_time ON reservations (expires_at) WHERE status = 'EXPIRED';
CREATE INDEX ix_reservations_expiry ON reservations (expires_at, id) WHERE status = 'READY';
CREATE INDEX ix_reservations_fifo ON reservations (book_id, reserved_at, id) WHERE status = 'WAITING';
CREATE INDEX ix_reservations_reserved_time ON reservations (reserved_at);
CREATE INDEX ix_reservations_status_time ON reservations (status, reserved_at);
CREATE INDEX ix_reservations_user_history ON reservations (user_id, reserved_at);
CREATE UNIQUE INDEX uq_reservations_active_user_book ON reservations (user_id, book_id) WHERE status IN ('WAITING','READY');
CREATE UNIQUE INDEX uq_reservations_ready_copy ON reservations (book_copy_id) WHERE status = 'READY';
```

## user_interactions

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| book_id | UUID | no |  |
| interaction_type | interaction_type | no |  |
| source | interaction_source | no |  |
| search_event_id | UUID | yes |  |
| recommendation_impression_id | UUID | yes |  |
| event_key | VARCHAR(150) | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_user_interactions`: PRIMARY KEY (id).
- `fk_user_interactions_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_user_interactions_impression_owner_book`: (recommendation_impression_id, user_id, book_id) → (recommendation_impressions.id, recommendation_impressions.user_id, recommendation_impressions.book_id), DELETE RESTRICT.
- `fk_user_interactions_search_event_id_search_events`: (search_event_id) → (search_events.id), DELETE RESTRICT.
- `fk_user_interactions_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_user_interactions_click_attribution`: CHECK `interaction_type <> 'RECOMMENDATION_CLICK' OR (recommendation_impression_id IS NOT NULL AND source IN ('RECOMMENDATION','SIMILAR_BOOKS','POPULAR_BOOKS'))`.
- `uq_user_interactions_event_key`: UNIQUE (event_key).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_user_interactions_book_time ON user_interactions (book_id, created_at);
CREATE INDEX ix_user_interactions_impression ON user_interactions (recommendation_impression_id);
CREATE INDEX ix_user_interactions_search_event_id ON user_interactions (search_event_id);
CREATE INDEX ix_user_interactions_time ON user_interactions (created_at);
CREATE INDEX ix_user_interactions_type_time ON user_interactions (interaction_type, created_at);
CREATE INDEX ix_user_interactions_user_time ON user_interactions (user_id, created_at);
CREATE UNIQUE INDEX uq_user_interactions_impression_click ON user_interactions (recommendation_impression_id) WHERE interaction_type = 'RECOMMENDATION_CLICK';
```

## borrowings

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| book_copy_id | UUID | no |  |
| reservation_id | UUID | yes |  |
| issued_by | UUID | no |  |
| returned_by | UUID | yes |  |
| borrowed_at | TIMESTAMP WITH TIME ZONE | no | now() |
| due_at | TIMESTAMP WITH TIME ZONE | no |  |
| returned_at | TIMESTAMP WITH TIME ZONE | yes |  |
| lost_at | TIMESTAMP WITH TIME ZONE | yes |  |
| status | borrowing_status | no | BORROWED |
| id | UUID | no | gen_random_uuid() |
| updated_at | TIMESTAMP WITH TIME ZONE | no | now() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_borrowings`: PRIMARY KEY (id).
- `fk_borrowings_book_copy_id_book_copies`: (book_copy_id) → (book_copies.id), DELETE RESTRICT.
- `fk_borrowings_issued_by_users`: (issued_by) → (users.id), DELETE RESTRICT.
- `fk_borrowings_reservation_assignment`: (reservation_id, user_id, book_copy_id) → (reservations.id, reservations.user_id, reservations.book_copy_id), DELETE RESTRICT.
- `fk_borrowings_returned_by_users`: (returned_by) → (users.id), DELETE RESTRICT.
- `fk_borrowings_user_id_users`: (user_id) → (users.id), DELETE RESTRICT.
- `ck_borrowings_due_date`: CHECK `due_at > borrowed_at`.
- `ck_borrowings_state_fields`: CHECK `(status = 'RETURNED' AND returned_at IS NOT NULL AND returned_by IS NOT NULL AND returned_at >= borrowed_at AND lost_at IS NULL) OR (status IN ('BORROWED','OVERDUE') AND returned_at IS NULL AND returned_by IS NULL AND lost_at IS NULL) OR (status = 'LOST' AND returned_at IS NULL AND returned_by IS NULL AND lost_at IS NOT NULL AND lost_at >= borrowed_at)`.
- `uq_borrowings_identity_user`: UNIQUE (id, user_id).
- `uq_borrowings_reservation_id`: UNIQUE (reservation_id).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_borrowings_borrowed ON borrowings (borrowed_at);
CREATE INDEX ix_borrowings_copy_history ON borrowings (book_copy_id, borrowed_at);
CREATE INDEX ix_borrowings_due ON borrowings (due_at, id) WHERE status IN ('BORROWED','OVERDUE');
CREATE INDEX ix_borrowings_issued_by ON borrowings (issued_by);
CREATE INDEX ix_borrowings_lost_time ON borrowings (lost_at) WHERE lost_at IS NOT NULL;
CREATE INDEX ix_borrowings_returned ON borrowings (returned_at);
CREATE INDEX ix_borrowings_returned_by ON borrowings (returned_by);
CREATE INDEX ix_borrowings_status ON borrowings (status);
CREATE INDEX ix_borrowings_user_status ON borrowings (user_id, status, borrowed_at);
CREATE UNIQUE INDEX uq_borrowings_active_copy ON borrowings (book_copy_id) WHERE status IN ('BORROWED','OVERDUE');
```

## notifications

| Column | PostgreSQL type | Nullable | Default |
|---|---|---|---|
| user_id | UUID | no |  |
| type | notification_type | no |  |
| title | VARCHAR(300) | no |  |
| message | TEXT | no |  |
| is_read | BOOLEAN | no | false |
| event_key | VARCHAR(200) | no |  |
| related_entity_type | related_entity | no |  |
| related_entity_id | UUID | no | generated: coalesce(reservation_id, borrowing_id, book_id) |
| reservation_id | UUID | yes |  |
| borrowing_id | UUID | yes |  |
| book_id | UUID | yes |  |
| id | UUID | no | gen_random_uuid() |
| created_at | TIMESTAMP WITH TIME ZONE | no | now() |

Constraints:

- `pk_notifications`: PRIMARY KEY (id).
- `fk_notifications_book_id_books`: (book_id) → (books.id), DELETE RESTRICT.
- `fk_notifications_borrowing_owner`: (borrowing_id, user_id) → (borrowings.id, borrowings.user_id), DELETE RESTRICT.
- `fk_notifications_reservation_owner`: (reservation_id, user_id) → (reservations.id, reservations.user_id), DELETE RESTRICT.
- `fk_notifications_user_id_users`: (user_id) → (users.id), DELETE CASCADE.
- `ck_notifications_content`: CHECK `length(btrim(title)) > 0 AND length(btrim(message)) > 0 AND length(btrim(event_key)) > 0`.
- `ck_notifications_entity_reference`: CHECK `(related_entity_type = 'RESERVATION' AND reservation_id IS NOT NULL AND borrowing_id IS NULL AND book_id IS NULL) OR (related_entity_type = 'BORROWING' AND borrowing_id IS NOT NULL AND reservation_id IS NULL AND book_id IS NULL) OR (related_entity_type = 'BOOK' AND book_id IS NOT NULL AND borrowing_id IS NULL AND reservation_id IS NULL)`.
- `uq_notifications_user_id`: UNIQUE (user_id, event_key).

Additional indexes (primary/unique constraint indexes are implicit):

```sql
CREATE INDEX ix_notifications_book_id ON notifications (book_id);
CREATE INDEX ix_notifications_borrowing ON notifications (borrowing_id);
CREATE INDEX ix_notifications_reservation ON notifications (reservation_id);
CREATE INDEX ix_notifications_user_read_time ON notifications (user_id, is_read, created_at);
```
