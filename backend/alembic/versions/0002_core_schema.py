"""Complete core schema with explicit, frozen DDL.

Revision ID: 0002_core_schema
Revises: 0001_extensions
"""

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_core_schema"
down_revision = "0001_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE reservation_number_seq")
    postgresql.ENUM("BORROWED", "RETURNED", "OVERDUE", "LOST", name="borrowing_status").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("NEW", "GOOD", "FAIR", "POOR", "DAMAGED", name="copy_condition").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(
        "AVAILABLE", "RESERVED", "BORROWED", "DAMAGED", "LOST", "MAINTENANCE", name="copy_status"
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "CATALOG",
        "STANDARD_SEARCH",
        "SEMANTIC_SEARCH",
        "HYBRID_SEARCH",
        "RECOMMENDATION",
        "AI_ASSISTANT",
        "SIMILAR_BOOKS",
        "POPULAR_BOOKS",
        name="interaction_source",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "VIEW",
        "SEARCH_CLICK",
        "FAVORITE",
        "RESERVE",
        "BORROW",
        "RECOMMENDATION_CLICK",
        name="interaction_type",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("USER", "ASSISTANT", name="message_role").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "RESERVATION_READY",
        "RESERVATION_EXPIRING",
        "RESERVATION_EXPIRED",
        "DUE_SOON",
        "OVERDUE",
        name="notification_type",
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("PENDING", "ACCEPTED", "MODIFIED", "REJECTED", name="prediction_review").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("PERSONALIZED", "SIMILAR_BOOK", "POPULAR", name="recommendation_type").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("RESERVATION", "BORROWING", "BOOK", name="related_entity").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(
        "WAITING", "READY", "COMPLETED", "CANCELLED", "EXPIRED", name="reservation_status"
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        "PROBABILITY", "COSINE_SIMILARITY", "DECISION_FUNCTION", name="score_kind"
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM("STANDARD", "SEMANTIC", "HYBRID", name="search_type").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("INTEGER", "BOOLEAN", "STRING", "JSON", name="setting_type").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("READER", "LIBRARIAN", "ADMIN", name="user_role").create(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("ACTIVE", "BLOCKED", "INACTIVE", name="user_status").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "authors",
        sa.Column("full_name", sa.String(length=300), nullable=False),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(btrim(full_name)) > 0", name=op.f("ck_authors_name")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authors")),
    )
    op.create_table(
        "categories",
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(btrim(name)) > 0", name=op.f("ck_categories_name")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_table(
        "embedding_models",
        sa.Column("model_name", sa.String(length=250), nullable=False),
        sa.Column("revision", sa.String(length=150), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("source_recipe", sa.String(length=100), nullable=False),
        sa.Column("normalized", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(configuration) = 'object'", name=op.f("ck_embedding_models_configuration")
        ),
        sa.CheckConstraint(
            "dimension BETWEEN 1 AND 16000", name=op.f("ck_embedding_models_dimension")
        ),
        sa.CheckConstraint(
            (
                "length(btrim(model_name)) > 0 AND length(btrim(revision)) > 0 AND"
                " length(btrim(source_recipe)) > 0"
            ),
            name=op.f("ck_embedding_models_provenance"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embedding_models")),
        sa.UniqueConstraint("id", "dimension", name="uq_embedding_models_dimension"),
        sa.UniqueConstraint(
            "model_name", "revision", "source_recipe", name="uq_embedding_models_space"
        ),
    )
    op.create_table(
        "publishers",
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(btrim(name)) > 0", name=op.f("ck_publishers_name")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publishers")),
    )
    op.create_table(
        "users",
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM("READER", "LIBRARIAN", "ADMIN", name="user_role", create_type=False),
            server_default="READER",
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("ACTIVE", "BLOCKED", "INACTIVE", name="user_status", create_type=False),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email = lower(btrim(email)) AND position('@' in email) > 1",
            name=op.f("ck_users_email"),
        ),
        sa.CheckConstraint(
            "password_hash LIKE '$argon2id$%'", name=op.f("ck_users_password_algorithm")
        ),
        sa.CheckConstraint(
            "length(btrim(first_name)) > 0 AND length(btrim(last_name)) > 0",
            name=op.f("ck_users_names"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "ai_conversations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_conversations_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_conversations")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("action ~ '^[A-Z][A-Z0-9_]+$'", name=op.f("ck_audit_logs_action")),
        sa.CheckConstraint(
            "details IS NULL OR jsonb_typeof(details) = 'object'",
            name=op.f("ck_audit_logs_details_object"),
        ),
        sa.CheckConstraint(
            "length(btrim(entity_type)) > 0", name=op.f("ck_audit_logs_entity_type")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_table(
        "books",
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("isbn", sa.String(length=13), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("publisher_id", sa.Uuid(), nullable=True),
        sa.Column("language", sa.String(length=35), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "isbn IS NULL OR isbn ~ '^([0-9]{13}|[0-9]{9}[0-9X])$'", name=op.f("ck_books_isbn")
        ),
        sa.CheckConstraint(
            "language ~ '^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$'", name=op.f("ck_books_language")
        ),
        sa.CheckConstraint("length(btrim(title)) > 0", name=op.f("ck_books_title")),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count > 0", name=op.f("ck_books_page_count")
        ),
        sa.CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1 AND 9999",
            name=op.f("ck_books_publication_year"),
        ),
        sa.ForeignKeyConstraint(
            ["publisher_id"],
            ["publishers.id"],
            name=op.f("fk_books_publisher_id_publishers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_books")),
        sa.UniqueConstraint("isbn", name=op.f("uq_books_isbn")),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_refresh_sessions_token_hash")
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name=op.f("ck_refresh_sessions_consumption"),
        ),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_refresh_sessions_expiry")),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name=op.f("ck_refresh_sessions_no_self_parent")
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name=op.f("ck_refresh_sessions_revocation"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id", "user_id", "family_id"],
            ["refresh_sessions.id", "refresh_sessions.user_id", "refresh_sessions.family_id"],
            name="fk_refresh_sessions_parent_family",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_sessions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_sessions")),
        sa.UniqueConstraint(
            "id", "user_id", "family_id", name="uq_refresh_sessions_identity_family"
        ),
        sa.UniqueConstraint("parent_id", name=op.f("uq_refresh_sessions_parent_id")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_sessions_token_hash")),
    )
    op.create_table(
        "search_events",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("query", sa.String(length=2000), nullable=False),
        sa.Column(
            "search_type",
            postgresql.ENUM(
                "STANDARD", "SEMANTIC", "HYBRID", name="search_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(filters) = 'object'", name=op.f("ck_search_events_filters_object")
        ),
        sa.CheckConstraint("length(btrim(query)) > 0", name=op.f("ck_search_events_query")),
        sa.CheckConstraint("result_count >= 0", name=op.f("ck_search_events_result_count")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_search_events_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_events")),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "value_type",
            postgresql.ENUM(
                "INTEGER", "BOOLEAN", "STRING", "JSON", name="setting_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("minimum", sa.Numeric(asdecimal=False), nullable=True),
        sa.Column("maximum", sa.Numeric(asdecimal=False), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "CASE value_type WHEN 'INTEGER' THEN CASE WHEN jsonb_typeof(value)"
                " = 'number' THEN (value::text)::numeric = "
                "trunc((value::text)::numeric) AND (minimum IS NULL OR "
                "(value::text)::numeric >= minimum) AND (maximum IS NULL OR "
                "(value::text)::numeric <= maximum) ELSE false END WHEN 'BOOLEAN' "
                "THEN jsonb_typeof(value) = 'boolean' WHEN 'STRING' THEN "
                "jsonb_typeof(value) = 'string' WHEN 'JSON' THEN "
                "jsonb_typeof(value) IN ('object','array') END"
            ),
            name=op.f("ck_system_settings_typed_value"),
        ),
        sa.CheckConstraint("key ~ '^[a-z][a-z0-9_]+$'", name=op.f("ck_system_settings_key")),
        sa.CheckConstraint(
            "minimum IS NULL OR maximum IS NULL OR minimum <= maximum",
            name=op.f("ck_system_settings_bounds"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_system_settings_updated_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_settings")),
        sa.UniqueConstraint("key", name=op.f("uq_system_settings_key")),
    )
    op.create_table(
        "user_category_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(precision=8, scale=4, asdecimal=False),
            server_default="1",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "weight >= 0 AND weight < 'Infinity'::numeric",
            name=op.f("ck_user_category_preferences_weight"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_user_category_preferences_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_category_preferences_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_category_preferences")),
        sa.UniqueConstraint(
            "user_id", "category_id", name=op.f("uq_user_category_preferences_user_id")
        ),
    )
    op.create_table(
        "ai_messages",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("USER", "ASSISTANT", name="message_role", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tool_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=250), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(tool_metadata) = 'object'", name=op.f("ck_ai_messages_tool_metadata")
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0", name=op.f("ck_ai_messages_input_tokens")
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0", name=op.f("ck_ai_messages_latency")
        ),
        sa.CheckConstraint("length(btrim(content)) > 0", name=op.f("ck_ai_messages_content")),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0", name=op.f("ck_ai_messages_output_tokens")
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["ai_conversations.id"],
            name=op.f("fk_ai_messages_conversation_id_ai_conversations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_messages")),
    )
    op.create_table(
        "book_authors",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["authors.id"],
            name=op.f("fk_book_authors_author_id_authors"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_book_authors_book_id_books"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_authors")),
        sa.UniqueConstraint("book_id", "author_id", name=op.f("uq_book_authors_book_id")),
    )
    op.create_table(
        "book_categories",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_book_categories_book_id_books"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_book_categories_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_categories")),
        sa.UniqueConstraint("book_id", "category_id", name=op.f("uq_book_categories_book_id")),
    )
    op.create_table(
        "book_copies",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_number", sa.String(length=100), nullable=False),
        sa.Column("shelf_location", sa.String(length=150), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "AVAILABLE",
                "RESERVED",
                "BORROWED",
                "DAMAGED",
                "LOST",
                "MAINTENANCE",
                name="copy_status",
                create_type=False,
            ),
            server_default="AVAILABLE",
            nullable=False,
        ),
        sa.Column(
            "condition",
            postgresql.ENUM(
                "NEW", "GOOD", "FAIR", "POOR", "DAMAGED", name="copy_condition", create_type=False
            ),
            server_default="GOOD",
            nullable=False,
        ),
        sa.Column("acquired_at", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "archived_at IS NULL OR status NOT IN ('RESERVED','BORROWED')",
            name=op.f("ck_book_copies_archive_not_circulating"),
        ),
        sa.CheckConstraint(
            "condition <> 'DAMAGED' OR status IN ('DAMAGED','MAINTENANCE','LOST')",
            name=op.f("ck_book_copies_damaged_not_circulating"),
        ),
        sa.CheckConstraint(
            "length(btrim(inventory_number)) > 0", name=op.f("ck_book_copies_inventory_number")
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_book_copies_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_copies")),
        sa.UniqueConstraint("id", "book_id", name="uq_book_copies_identity_book"),
        sa.UniqueConstraint("inventory_number", name=op.f("uq_book_copies_inventory_number")),
    )
    op.create_table(
        "book_embeddings",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "source_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_book_embeddings_source_hash")
        ),
        sa.CheckConstraint(
            "vector_dims(embedding) = dimension", name=op.f("ck_book_embeddings_dimension")
        ),
        sa.CheckConstraint(
            "vector_norm(embedding) > 0", name=op.f("ck_book_embeddings_nonzero_vector")
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_book_embeddings_book_id_books"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id", "dimension"],
            ["embedding_models.id", "embedding_models.dimension"],
            name="fk_book_embeddings_model_dimension",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_book_embeddings")),
        sa.UniqueConstraint("book_id", "model_id", name=op.f("uq_book_embeddings_book_id")),
    )
    op.create_table(
        "category_prediction_runs",
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=250), nullable=False),
        sa.Column("model_revision", sa.String(length=150), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "review_status",
            postgresql.ENUM(
                "PENDING",
                "ACCEPTED",
                "MODIFIED",
                "REJECTED",
                name="prediction_review",
                create_type=False,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "(review_status = 'PENDING' AND reviewed_by IS NULL AND "
                "reviewed_at IS NULL) OR (review_status <> 'PENDING' AND "
                "reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND "
                "reviewed_at >= created_at)"
            ),
            name=op.f("ck_category_prediction_runs_review"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(configuration) = 'object'",
            name=op.f("ck_category_prediction_runs_configuration"),
        ),
        sa.CheckConstraint(
            "source_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_category_prediction_runs_source_hash")
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_category_prediction_runs_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_category_prediction_runs_requested_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_category_prediction_runs_reviewed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_prediction_runs")),
        sa.UniqueConstraint("id", "book_id", name="uq_category_prediction_runs_identity_book"),
    )
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_favorites_book_id_books"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_favorites_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorites")),
        sa.UniqueConstraint("user_id", "book_id", name=op.f("uq_favorites_user_id")),
    )
    op.create_table(
        "recommendation_impressions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column(
            "recommendation_type",
            postgresql.ENUM(
                "PERSONALIZED",
                "SIMILAR_BOOK",
                "POPULAR",
                name="recommendation_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(
                "CATALOG",
                "STANDARD_SEARCH",
                "SEMANTIC_SEARCH",
                "HYBRID_SEARCH",
                "RECOMMENDATION",
                "AI_ASSISTANT",
                "SIMILAR_BOOKS",
                "POPULAR_BOOKS",
                name="interaction_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=150), nullable=False),
        sa.Column("model_name", sa.String(length=250), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "length(btrim(event_key)) > 0", name=op.f("ck_recommendation_impressions_event_key")
        ),
        sa.CheckConstraint("position >= 1", name=op.f("ck_recommendation_impressions_position")),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_recommendation_impressions_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recommendation_impressions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_impressions")),
        sa.UniqueConstraint("event_key", name=op.f("uq_recommendation_impressions_event_key")),
        sa.UniqueConstraint(
            "id", "user_id", "book_id", name="uq_recommendation_impressions_identity"
        ),
    )
    op.create_table(
        "ai_message_books",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("position >= 1", name=op.f("ck_ai_message_books_position")),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_ai_message_books_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["ai_messages.id"],
            name=op.f("fk_ai_message_books_message_id_ai_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_message_books")),
        sa.UniqueConstraint("message_id", "book_id", name=op.f("uq_ai_message_books_message_id")),
        sa.UniqueConstraint("message_id", "position", name="uq_ai_message_books_position"),
    )
    op.create_table(
        "category_prediction_selections",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_category_prediction_selections_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["category_prediction_runs.id"],
            name=op.f("fk_category_prediction_selections_run_id_category_prediction_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_prediction_selections")),
        sa.UniqueConstraint(
            "run_id", "category_id", name=op.f("uq_category_prediction_selections_run_id")
        ),
    )
    op.create_table(
        "category_predictions",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "score_kind",
            postgresql.ENUM(
                "PROBABILITY",
                "COSINE_SIMILARITY",
                "DECISION_FUNCTION",
                name="score_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "confidence > '-Infinity'::float8 AND confidence < "
                "'Infinity'::float8 AND (score_kind = 'DECISION_FUNCTION' OR "
                "(score_kind = 'PROBABILITY' AND confidence BETWEEN 0 AND 1) OR "
                "(score_kind = 'COSINE_SIMILARITY' AND confidence BETWEEN -1 AND "
                "1))"
            ),
            name=op.f("ck_category_predictions_score"),
        ),
        sa.CheckConstraint(
            (
                "(accepted IS NULL AND reviewed_by IS NULL AND reviewed_at IS "
                "NULL) OR (accepted IS NOT NULL AND reviewed_by IS NOT NULL AND "
                "reviewed_at IS NOT NULL AND reviewed_at >= created_at)"
            ),
            name=op.f("ck_category_predictions_review"),
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_category_predictions_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_category_predictions_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_category_predictions_reviewed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "book_id"],
            ["category_prediction_runs.id", "category_prediction_runs.book_id"],
            name="fk_category_predictions_run_book",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_category_predictions")),
        sa.UniqueConstraint("run_id", "category_id", name=op.f("uq_category_predictions_run_id")),
    )
    op.create_table(
        "reservations",
        sa.Column(
            "reservation_number",
            sa.String(length=64),
            server_default=sa.text("'R-' || nextval('reservation_number_seq')::text"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("book_copy_id", sa.Uuid(), nullable=True),
        sa.Column("qr_token_hash", sa.String(length=64), nullable=True),
        sa.Column("qr_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("qr_key_id", sa.String(length=50), nullable=True),
        sa.Column(
            "reserved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "WAITING",
                "READY",
                "COMPLETED",
                "CANCELLED",
                "EXPIRED",
                name="reservation_status",
                create_type=False,
            ),
            server_default="WAITING",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "(status = 'READY' AND qr_token_hash IS NOT NULL AND "
                "qr_token_ciphertext IS NOT NULL AND qr_key_id IS NOT NULL) OR "
                "(status <> 'READY' AND qr_token_hash IS NULL AND "
                "qr_token_ciphertext IS NULL AND qr_key_id IS NULL)"
            ),
            name=op.f("ck_reservations_qr_lifecycle"),
        ),
        sa.CheckConstraint(
            (
                "(status = 'WAITING' AND book_copy_id IS NULL AND ready_at IS NULL"
                " AND expires_at IS NULL AND completed_at IS NULL AND cancelled_at"
                " IS NULL) OR (status = 'READY' AND book_copy_id IS NOT NULL AND "
                "ready_at IS NOT NULL AND expires_at IS NOT NULL AND completed_at "
                "IS NULL AND cancelled_at IS NULL) OR (status = 'COMPLETED' AND "
                "book_copy_id IS NOT NULL AND ready_at IS NOT NULL AND expires_at "
                "IS NOT NULL AND completed_at IS NOT NULL AND cancelled_at IS "
                "NULL) OR (status = 'CANCELLED' AND cancelled_at IS NOT NULL AND "
                "completed_at IS NULL) OR (status = 'EXPIRED' AND book_copy_id IS "
                "NOT NULL AND ready_at IS NOT NULL AND expires_at IS NOT NULL AND "
                "completed_at IS NULL AND cancelled_at IS NULL)"
            ),
            name=op.f("ck_reservations_state_fields"),
        ),
        sa.CheckConstraint(
            "qr_token_hash IS NULL OR qr_token_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_reservations_qr_hash"),
        ),
        sa.CheckConstraint(
            (
                "(ready_at IS NULL AND book_copy_id IS NULL AND expires_at IS "
                "NULL) OR (ready_at IS NOT NULL AND book_copy_id IS NOT NULL AND "
                "expires_at IS NOT NULL AND ready_at >= reserved_at AND expires_at"
                " > ready_at)"
            ),
            name=op.f("ck_reservations_hold_dates"),
        ),
        sa.CheckConstraint(
            "cancelled_at IS NULL OR cancelled_at >= reserved_at",
            name=op.f("ck_reservations_cancelled_date"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= ready_at",
            name=op.f("ck_reservations_completed_date"),
        ),
        sa.CheckConstraint(
            "length(btrim(reservation_number)) > 0", name=op.f("ck_reservations_number")
        ),
        sa.ForeignKeyConstraint(
            ["book_copy_id", "book_id"],
            ["book_copies.id", "book_copies.book_id"],
            name="fk_reservations_copy_book",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_reservations_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reservations_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reservations")),
        sa.UniqueConstraint(
            "id", "user_id", "book_copy_id", name="uq_reservations_identity_assignment"
        ),
        sa.UniqueConstraint("id", "user_id", name="uq_reservations_identity_user"),
        sa.UniqueConstraint("qr_token_hash", name=op.f("uq_reservations_qr_token_hash")),
        sa.UniqueConstraint("reservation_number", name=op.f("uq_reservations_reservation_number")),
    )
    op.create_table(
        "user_interactions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column(
            "interaction_type",
            postgresql.ENUM(
                "VIEW",
                "SEARCH_CLICK",
                "FAVORITE",
                "RESERVE",
                "BORROW",
                "RECOMMENDATION_CLICK",
                name="interaction_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(
                "CATALOG",
                "STANDARD_SEARCH",
                "SEMANTIC_SEARCH",
                "HYBRID_SEARCH",
                "RECOMMENDATION",
                "AI_ASSISTANT",
                "SIMILAR_BOOKS",
                "POPULAR_BOOKS",
                name="interaction_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("search_event_id", sa.Uuid(), nullable=True),
        sa.Column("recommendation_impression_id", sa.Uuid(), nullable=True),
        sa.Column("event_key", sa.String(length=150), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "interaction_type <> 'RECOMMENDATION_CLICK' OR "
                "(recommendation_impression_id IS NOT NULL AND source IN "
                "('RECOMMENDATION','SIMILAR_BOOKS','POPULAR_BOOKS'))"
            ),
            name=op.f("ck_user_interactions_click_attribution"),
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_user_interactions_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_impression_id", "user_id", "book_id"],
            [
                "recommendation_impressions.id",
                "recommendation_impressions.user_id",
                "recommendation_impressions.book_id",
            ],
            name="fk_user_interactions_impression_owner_book",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["search_event_id"],
            ["search_events.id"],
            name=op.f("fk_user_interactions_search_event_id_search_events"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_interactions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_interactions")),
        sa.UniqueConstraint("event_key", name=op.f("uq_user_interactions_event_key")),
    )
    op.create_table(
        "borrowings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("book_copy_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("issued_by", sa.Uuid(), nullable=False),
        sa.Column("returned_by", sa.Uuid(), nullable=True),
        sa.Column(
            "borrowed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lost_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "BORROWED",
                "RETURNED",
                "OVERDUE",
                "LOST",
                name="borrowing_status",
                create_type=False,
            ),
            server_default="BORROWED",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "(status = 'RETURNED' AND returned_at IS NOT NULL AND returned_by "
                "IS NOT NULL AND returned_at >= borrowed_at AND lost_at IS NULL) "
                "OR (status IN ('BORROWED','OVERDUE') AND returned_at IS NULL AND "
                "returned_by IS NULL AND lost_at IS NULL) OR (status = 'LOST' AND "
                "returned_at IS NULL AND returned_by IS NULL AND lost_at IS NOT "
                "NULL AND lost_at >= borrowed_at)"
            ),
            name=op.f("ck_borrowings_state_fields"),
        ),
        sa.CheckConstraint("due_at > borrowed_at", name=op.f("ck_borrowings_due_date")),
        sa.ForeignKeyConstraint(
            ["book_copy_id"],
            ["book_copies.id"],
            name=op.f("fk_borrowings_book_copy_id_book_copies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name=op.f("fk_borrowings_issued_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id", "user_id", "book_copy_id"],
            ["reservations.id", "reservations.user_id", "reservations.book_copy_id"],
            name="fk_borrowings_reservation_assignment",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["returned_by"],
            ["users.id"],
            name=op.f("fk_borrowings_returned_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_borrowings_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_borrowings")),
        sa.UniqueConstraint("id", "user_id", name="uq_borrowings_identity_user"),
        sa.UniqueConstraint("reservation_id", name=op.f("uq_borrowings_reservation_id")),
    )
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "RESERVATION_READY",
                "RESERVATION_EXPIRING",
                "RESERVATION_EXPIRED",
                "DUE_SOON",
                "OVERDUE",
                name="notification_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("event_key", sa.String(length=200), nullable=False),
        sa.Column(
            "related_entity_type",
            postgresql.ENUM(
                "RESERVATION", "BORROWING", "BOOK", name="related_entity", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "related_entity_id",
            sa.Uuid(),
            sa.Computed("coalesce(reservation_id, borrowing_id, book_id)", persisted=True),
            nullable=False,
        ),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("borrowing_id", sa.Uuid(), nullable=True),
        sa.Column("book_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "(related_entity_type = 'RESERVATION' AND reservation_id IS NOT "
                "NULL AND borrowing_id IS NULL AND book_id IS NULL) OR "
                "(related_entity_type = 'BORROWING' AND borrowing_id IS NOT NULL "
                "AND reservation_id IS NULL AND book_id IS NULL) OR "
                "(related_entity_type = 'BOOK' AND book_id IS NOT NULL AND "
                "borrowing_id IS NULL AND reservation_id IS NULL)"
            ),
            name=op.f("ck_notifications_entity_reference"),
        ),
        sa.CheckConstraint(
            (
                "length(btrim(title)) > 0 AND length(btrim(message)) > 0 AND "
                "length(btrim(event_key)) > 0"
            ),
            name=op.f("ck_notifications_content"),
        ),
        sa.ForeignKeyConstraint(
            ["book_id"],
            ["books.id"],
            name=op.f("fk_notifications_book_id_books"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["borrowing_id", "user_id"],
            ["borrowings.id", "borrowings.user_id"],
            name="fk_notifications_borrowing_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id", "user_id"],
            ["reservations.id", "reservations.user_id"],
            name="fk_notifications_reservation_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint("user_id", "event_key", name=op.f("uq_notifications_user_id")),
    )
    op.create_index(
        "ix_authors_name_trgm",
        "authors",
        ["full_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_categories_name_trgm",
        "categories",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_publishers_name_trgm",
        "publishers",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index("ix_users_name", "users", ["last_name", "first_name"], unique=False)
    op.create_index(
        "ix_users_role_status_created", "users", ["role", "status", "created_at"], unique=False
    )
    op.create_index("ix_users_status", "users", ["status"], unique=False)
    op.create_index(
        "ix_ai_conversations_user_updated",
        "ai_conversations",
        ["user_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_action_time", "audit_logs", ["action", "created_at"], unique=False
    )
    op.create_index(
        "ix_audit_logs_actor_time", "audit_logs", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_audit_logs_entity_time",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_audit_logs_time", "audit_logs", ["created_at", "id"], unique=False)
    op.create_index("ix_books_created", "books", ["created_at", "id"], unique=False)
    op.create_index(
        "ix_books_description_trgm",
        "books",
        ["description"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_books_language_year", "books", ["language", "publication_year"], unique=False
    )
    op.create_index("ix_books_publication_year", "books", ["publication_year"], unique=False)
    op.create_index(op.f("ix_books_publisher_id"), "books", ["publisher_id"], unique=False)
    op.create_index("ix_books_title", "books", ["title"], unique=False)
    op.create_index(
        "ix_books_title_trgm",
        "books",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index("ix_refresh_sessions_expiry", "refresh_sessions", ["expires_at"], unique=False)
    op.create_index(
        "ix_refresh_sessions_user_family",
        "refresh_sessions",
        ["user_id", "family_id"],
        unique=False,
    )
    op.create_index("ix_search_events_time", "search_events", ["created_at"], unique=False)
    op.create_index(
        "ix_search_events_type_time", "search_events", ["search_type", "created_at"], unique=False
    )
    op.create_index(op.f("ix_search_events_user_id"), "search_events", ["user_id"], unique=False)
    op.create_index(
        "ix_search_events_zero_results",
        "search_events",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("result_count = 0"),
    )
    op.create_index(
        op.f("ix_system_settings_updated_by"), "system_settings", ["updated_by"], unique=False
    )
    op.create_index(
        op.f("ix_user_category_preferences_category_id"),
        "user_category_preferences",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_messages_conversation_time",
        "ai_messages",
        ["conversation_id", "created_at", "id"],
        unique=False,
    )
    op.create_index("ix_ai_messages_role_time", "ai_messages", ["role", "created_at"], unique=False)
    op.create_index(op.f("ix_book_authors_author_id"), "book_authors", ["author_id"], unique=False)
    op.create_index(
        op.f("ix_book_categories_category_id"), "book_categories", ["category_id"], unique=False
    )
    op.create_index(
        "ix_book_copies_allocation",
        "book_copies",
        ["book_id", "status", "acquired_at", "created_at", "id"],
        unique=False,
    )
    op.create_index("ix_book_copies_status", "book_copies", ["status"], unique=False)
    op.create_index(
        "ix_book_embeddings_model", "book_embeddings", ["model_id", "book_id"], unique=False
    )
    op.create_index(
        op.f("ix_category_prediction_runs_book_id"),
        "category_prediction_runs",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_category_prediction_runs_requested_by"),
        "category_prediction_runs",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        "ix_category_prediction_runs_review_time",
        "category_prediction_runs",
        ["review_status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_category_prediction_runs_reviewed_by"),
        "category_prediction_runs",
        ["reviewed_by"],
        unique=False,
    )
    op.create_index(op.f("ix_favorites_book_id"), "favorites", ["book_id"], unique=False)
    op.create_index(
        op.f("ix_recommendation_impressions_book_id"),
        "recommendation_impressions",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_impressions_time",
        "recommendation_impressions",
        ["shown_at"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_impressions_type_time",
        "recommendation_impressions",
        ["recommendation_type", "shown_at"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_impressions_user_time",
        "recommendation_impressions",
        ["user_id", "shown_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_message_books_book_id"), "ai_message_books", ["book_id"], unique=False
    )
    op.create_index(
        op.f("ix_category_prediction_selections_category_id"),
        "category_prediction_selections",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_category_predictions_book_id"), "category_predictions", ["book_id"], unique=False
    )
    op.create_index(
        op.f("ix_category_predictions_category_id"),
        "category_predictions",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        "ix_category_predictions_review_time",
        "category_predictions",
        ["accepted", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_category_predictions_reviewed_by"),
        "category_predictions",
        ["reviewed_by"],
        unique=False,
    )
    op.create_index(
        "ix_reservations_book_status", "reservations", ["book_id", "status"], unique=False
    )
    op.create_index("ix_reservations_copy", "reservations", ["book_copy_id"], unique=False)
    op.create_index(
        "ix_reservations_expiry",
        "reservations",
        ["expires_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'READY'"),
    )
    op.create_index(
        "ix_reservations_fifo",
        "reservations",
        ["book_id", "reserved_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'WAITING'"),
    )
    op.create_index(
        "ix_reservations_status_time", "reservations", ["status", "reserved_at"], unique=False
    )
    op.create_index(
        "ix_reservations_user_history", "reservations", ["user_id", "reserved_at"], unique=False
    )
    op.create_index(
        "uq_reservations_active_user_book",
        "reservations",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('WAITING','READY')"),
    )
    op.create_index(
        "uq_reservations_ready_copy",
        "reservations",
        ["book_copy_id"],
        unique=True,
        postgresql_where=sa.text("status = 'READY'"),
    )
    op.create_index(
        "ix_user_interactions_book_time",
        "user_interactions",
        ["book_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_interactions_impression",
        "user_interactions",
        ["recommendation_impression_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_interactions_search_event_id"),
        "user_interactions",
        ["search_event_id"],
        unique=False,
    )
    op.create_index("ix_user_interactions_time", "user_interactions", ["created_at"], unique=False)
    op.create_index(
        "ix_user_interactions_type_time",
        "user_interactions",
        ["interaction_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_interactions_user_time",
        "user_interactions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_user_interactions_impression_click",
        "user_interactions",
        ["recommendation_impression_id"],
        unique=True,
        postgresql_where=sa.text("interaction_type = 'RECOMMENDATION_CLICK'"),
    )
    op.create_index("ix_borrowings_borrowed", "borrowings", ["borrowed_at"], unique=False)
    op.create_index(
        "ix_borrowings_copy_history", "borrowings", ["book_copy_id", "borrowed_at"], unique=False
    )
    op.create_index(
        "ix_borrowings_due",
        "borrowings",
        ["due_at", "id"],
        unique=False,
        postgresql_where=sa.text("status IN ('BORROWED','OVERDUE')"),
    )
    op.create_index(op.f("ix_borrowings_issued_by"), "borrowings", ["issued_by"], unique=False)
    op.create_index("ix_borrowings_returned", "borrowings", ["returned_at"], unique=False)
    op.create_index(op.f("ix_borrowings_returned_by"), "borrowings", ["returned_by"], unique=False)
    op.create_index("ix_borrowings_status", "borrowings", ["status"], unique=False)
    op.create_index(
        "ix_borrowings_user_status",
        "borrowings",
        ["user_id", "status", "borrowed_at"],
        unique=False,
    )
    op.create_index(
        "uq_borrowings_active_copy",
        "borrowings",
        ["book_copy_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('BORROWED','OVERDUE')"),
    )
    op.create_index(op.f("ix_notifications_book_id"), "notifications", ["book_id"], unique=False)
    op.create_index("ix_notifications_borrowing", "notifications", ["borrowing_id"], unique=False)
    op.create_index(
        "ix_notifications_reservation", "notifications", ["reservation_id"], unique=False
    )
    op.create_index(
        "ix_notifications_user_read_time",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("borrowings")
    op.drop_table("user_interactions")
    op.drop_table("reservations")
    op.drop_table("category_predictions")
    op.drop_table("category_prediction_selections")
    op.drop_table("ai_message_books")
    op.drop_table("recommendation_impressions")
    op.drop_table("favorites")
    op.drop_table("category_prediction_runs")
    op.drop_table("book_embeddings")
    op.drop_table("book_copies")
    op.drop_table("book_categories")
    op.drop_table("book_authors")
    op.drop_table("ai_messages")
    op.drop_table("user_category_preferences")
    op.drop_table("system_settings")
    op.drop_table("search_events")
    op.drop_table("refresh_sessions")
    op.drop_table("books")
    op.drop_table("audit_logs")
    op.drop_table("ai_conversations")
    op.drop_table("users")
    op.drop_table("publishers")
    op.drop_table("embedding_models")
    op.drop_table("categories")
    op.drop_table("authors")

    postgresql.ENUM(name="user_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="setting_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="search_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="score_kind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="reservation_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="related_entity").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="recommendation_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="prediction_review").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="message_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="interaction_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="interaction_source").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="copy_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="copy_condition").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="borrowing_status").drop(op.get_bind(), checkfirst=True)
    op.execute("DROP SEQUENCE reservation_number_seq")
