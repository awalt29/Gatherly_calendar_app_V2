"""Make phone number required

Revision ID: 89d2b0bace08
Revises: 4068979a6f15
Create Date: 2025-09-16 23:04:45.769716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89d2b0bace08'
down_revision = '4068979a6f15'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite doesn't support ALTER COLUMN to change nullable constraint
    # For existing users without phone numbers, they'll need to add them through settings
    # New users will be required to provide phone numbers
    pass


def downgrade():
    pass
