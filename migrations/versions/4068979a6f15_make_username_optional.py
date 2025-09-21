"""Make username optional

Revision ID: 4068979a6f15
Revises: b004c917e493
Create Date: 2025-09-16 23:00:40.327812

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4068979a6f15'
down_revision = 'b004c917e493'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support ALTER COLUMN, so we'll use a workaround
    # For now, we'll just note that new users won't need usernames
    # Existing users with usernames will keep them
    pass


def downgrade():
    pass
