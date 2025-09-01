"""Add anyja_neve column to Case

Revision ID: 2b4d36c64bf1
Revises: f28b14d743a3
Create Date: 2025-08-29 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2b4d36c64bf1"
down_revision = "f28b14d743a3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("anyja_neve", sa.String(length=128), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.drop_column("anyja_neve")
