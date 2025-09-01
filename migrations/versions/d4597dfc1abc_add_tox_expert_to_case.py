"""Add tox_expert column to Case

Revision ID: d4597dfc1abc
Revises: c967f2236eca
Create Date: 2025-06-30 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "d4597dfc1abc"
down_revision = "c967f2236eca"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tox_expert", sa.String(length=128), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.drop_column("tox_expert")
