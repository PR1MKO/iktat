"""add full_name to user

Revision ID: b79a7cf96c00
Revises: a0c2905147be
Create Date: 2025-08-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b79a7cf96c00'
down_revision = 'a0c2905147be'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('full_name', sa.String(length=128), nullable=True))

def downgrade():
    op.drop_column('user', 'full_name')