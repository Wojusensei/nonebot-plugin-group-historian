"""init tables

Revision ID: 0001
Revises:
Create Date: 2026-06-27
"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = ('group_historian',)
depends_on = None

def upgrade() -> None:
    op.create_table(
        'daily_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('nickname', sa.String(), nullable=True),
        sa.Column('message_length', sa.Integer(), server_default='0', nullable=False),
        sa.Column('timestamp', sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('daily_messages')