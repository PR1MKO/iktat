"""add tox_viewed_at to case

Revision ID: abcd1234ef56
Revises: 7c3b2383fefe
Create Date: 2025-08-06 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "abcd1234ef56"
down_revision = "7c3b2383fefe"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tox_viewed_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.drop_column("tox_viewed_at")
