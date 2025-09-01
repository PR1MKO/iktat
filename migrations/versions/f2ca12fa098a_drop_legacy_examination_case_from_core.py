"""drop legacy examination_case from core

Revision ID: f2ca12fa098a
Revises: a0c2905147be
Create Date: 2025-08-18 10:23:07.000000

"""

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = "f2ca12fa098a"
down_revision = "a0c2905147be"
branch_labels = None
depends_on = None


def upgrade():
    if context.get_tag_argument() != "examination":
        return
    op.drop_table("examination_case")


def downgrade():
    if context.get_tag_argument() != "examination":
        return
    op.create_table(
        "examination_case",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("investigation_number", sa.String(length=20), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=True),
        sa.Column("institution", sa.String(length=128), nullable=True),
        sa.Column("ordering_authority", sa.String(length=128), nullable=True),
        sa.Column("deceased_name", sa.String(length=128), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("investigation_number"),
    )
