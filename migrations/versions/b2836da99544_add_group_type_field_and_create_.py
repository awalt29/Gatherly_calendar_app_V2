"""Add group_type field and create Activity model

Revision ID: b2836da99544
Revises: 1966d08cc9cb
Create Date: 2025-09-25 21:26:08.777839

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2836da99544'
down_revision = '1966d08cc9cb'
branch_labels = None
depends_on = None


def upgrade():
    # Add group_type field to existing group table
    op.add_column('group', sa.Column('group_type', sa.String(20), nullable=True, server_default='private'))
    
    # Create activity table
    op.create_table('activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('venue', sa.String(200), nullable=False),
        sa.Column('suggested_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('status', sa.String(20), nullable=True, server_default='pending'),
        sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['group_id'], ['group.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['suggested_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Drop activity table
    op.drop_table('activity')
    
    # Remove group_type column
    op.drop_column('group', 'group_type')
