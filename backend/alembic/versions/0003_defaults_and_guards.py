"""Initial configurable rules, automatic update timestamps and immutable audit/provenance.

Revision ID: 0003_defaults_and_guards
Revises: 0002_core_schema
"""

from alembic import op

revision = "0003_defaults_and_guards"
down_revision = "0002_core_schema"
branch_labels = None
depends_on = None

UPDATED_TABLES = (
    "users",
    "books",
    "book_copies",
    "reservations",
    "borrowings",
    "ai_conversations",
    "system_settings",
)


def upgrade() -> None:
    op.execute("""
        INSERT INTO system_settings (key, value, value_type, minimum, maximum, description) VALUES
        ('borrow_period_days', '14'::jsonb, 'INTEGER', 1, 365,
         'Days allowed for new borrowings.'),
        ('max_books_per_user', '5'::jsonb, 'INTEGER', 1, 100,
         'Maximum simultaneous active borrowings per reader.'),
        ('reservation_hold_hours', '48'::jsonb, 'INTEGER', 1, 8760,
         'Pickup hold after a reservation becomes READY.'),
        ('return_reminder_days', '2'::jsonb, 'INTEGER', 0, 365,
         'Days before the due date to send a reminder.'),
        ('block_borrowing_if_overdue', 'true'::jsonb, 'BOOLEAN', NULL, NULL,
         'Block new loans for overdue readers.'),
        ('block_reservation_if_overdue', 'true'::jsonb, 'BOOLEAN', NULL, NULL,
         'Block new reservations for overdue readers.')
    """)
    op.execute("""
        CREATE FUNCTION touch_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at := statement_timestamp();
            RETURN NEW;
        END $$
    """)
    for table in UPDATED_TABLES:
        op.execute(
            f"CREATE TRIGGER tr_{table}_updated BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
        )
    op.execute("""
        CREATE FUNCTION reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Immutable record cannot be changed' USING ERRCODE = '23514';
        END $$
    """)
    op.execute(
        "CREATE TRIGGER tr_audit_immutable BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()"
    )
    op.execute(
        "CREATE TRIGGER tr_audit_no_truncate BEFORE TRUNCATE ON audit_logs "
        "FOR EACH STATEMENT EXECUTE FUNCTION reject_immutable_change()"
    )
    op.execute(
        "CREATE TRIGGER tr_embedding_model_immutable BEFORE UPDATE ON embedding_models "
        "FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER tr_embedding_model_immutable ON embedding_models")
    op.execute("DROP TRIGGER tr_audit_no_truncate ON audit_logs")
    op.execute("DROP TRIGGER tr_audit_immutable ON audit_logs")
    op.execute("DROP FUNCTION reject_immutable_change()")
    for table in UPDATED_TABLES:
        op.execute(f"DROP TRIGGER tr_{table}_updated ON {table}")
    op.execute("DROP FUNCTION touch_updated_at()")
    # Downgrades run only on disposable test databases.
    # Operational rollback requires a backup.
    op.execute(
        "DELETE FROM system_settings WHERE key IN ('borrow_period_days', 'max_books_per_user', "
        "'reservation_hold_hours', 'return_reminder_days', 'block_borrowing_if_overdue', "
        "'block_reservation_if_overdue')"
    )
