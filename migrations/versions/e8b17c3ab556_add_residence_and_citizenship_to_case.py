"""Add residence and citizenship fields to Case

Revision ID: e8b17c3ab556
Revises: af99da151777
Create Date: 2025-09-04 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e8b17c3ab556"
down_revision = "af99da151777"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("residence", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("citizenship", sa.String(length=255), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.drop_column("citizenship")
        batch_op.drop_column("residence")
