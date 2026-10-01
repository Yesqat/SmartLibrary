"""Date-filtered circulation and categorization analytics indexes.

Revision ID: 0004_analytics_indexes
Revises: 0003_defaults_and_guards
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_analytics_indexes"
down_revision = "0003_defaults_and_guards"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_reservations_reserved_time", "reservations", "reserved_at", None),
    ("ix_reservations_completed_time", "reservations", "completed_at", "completed_at IS NOT NULL"),
    ("ix_reservations_cancelled_time", "reservations", "cancelled_at", "cancelled_at IS NOT NULL"),
    ("ix_reservations_expired_time", "reservations", "expires_at", "status = 'EXPIRED'"),
    ("ix_borrowings_lost_time", "borrowings", "lost_at", "lost_at IS NOT NULL"),
    ("ix_category_prediction_runs_created", "category_prediction_runs", "created_at", None),
    (
        "ix_category_prediction_runs_reviewed",
        "category_prediction_runs",
        "reviewed_at",
        "reviewed_at IS NOT NULL",
    ),
    ("ix_category_predictions_created", "category_predictions", "created_at", None),
    (
        "ix_category_predictions_reviewed",
        "category_predictions",
        "reviewed_at",
        "reviewed_at IS NOT NULL",
    ),
)


def upgrade() -> None:
    for name, table, column, condition in INDEXES:
        op.create_index(
            name, table, [column], postgresql_where=sa.text(condition) if condition else None
        )


def downgrade() -> None:
    for name, table, _, _ in reversed(INDEXES):
        op.drop_index(name, table_name=table)
