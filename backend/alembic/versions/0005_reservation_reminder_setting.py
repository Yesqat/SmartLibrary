"""Configurable upcoming pickup-expiry reminder threshold.

Revision ID: 0005_reservation_reminder
Revises: 0004_analytics_indexes
"""

from alembic import op

revision = "0005_reservation_reminder"
down_revision = "0004_analytics_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO system_settings (key, value, value_type, minimum, maximum, description)
        VALUES ('reservation_reminder_hours', '6'::jsonb, 'INTEGER', 0, 8760,
                'Hours before pickup expiry to notify once; zero disables this reminder.')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM system_settings WHERE key = 'reservation_reminder_hours'")
