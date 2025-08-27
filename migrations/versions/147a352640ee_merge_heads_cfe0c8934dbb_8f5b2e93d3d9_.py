"""🔀 Merge heads cfe0c8934dbb + 8f5b2e93d3d9 (timezone-aware datetimes)

Revision ID: 147a352640ee
Revises: 8f5b2e93d3d9, cfe0c8934dbb
Create Date: 2025-08-27 09:20:38.654900

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '147a352640ee'
down_revision = ('8f5b2e93d3d9', 'cfe0c8934dbb')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
