"""init database tables

Revision ID: 20250615_001
Create Date: 2025-06-15
"""

from alembic import op
import sqlalchemy as sa

revision = '20250615_001'
down_revision = None
branch_labels = ('group_historian',)
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass