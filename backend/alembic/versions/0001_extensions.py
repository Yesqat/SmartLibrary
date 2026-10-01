"""Enable PostgreSQL-native search extensions; requires extension-install privileges.

Revision ID: 0001_extensions
"""

from alembic import op

revision = "0001_extensions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    # Shared extensions may predate this application. Preserve them on rollback.
    pass
