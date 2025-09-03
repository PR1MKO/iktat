"""Restore investigation table on examination bind (guarded)

Revision ID: 6f2c9a1e3b21
Revises: 310105dd28d2
Create Date: 2025-09-03 10:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6f2c9a1e3b21"
down_revision = "310105dd28d2"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def upgrade():
    conn = op.get_bind()
    if not _table_exists(conn, "investigation"):
        op.create_table(
            "investigation",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("case_number", sa.String(length=16), nullable=False, unique=True),
            sa.Column("external_case_number", sa.String(length=64)),
            sa.Column("other_identifier", sa.String(length=64)),
            sa.Column("subject_name", sa.String(length=128), nullable=False),
            sa.Column("mother_name", sa.String(length=128)),
            sa.Column("registration_time", sa.DateTime(timezone=True)),
        )
        op.create_index(
            "ux_investigation_case_number",
            "investigation",
            ["case_number"],
            unique=True,
        )


def downgrade():
    conn = op.get_bind()
    if _table_exists(conn, "investigation"):
        op.drop_index("ux_investigation_case_number", table_name="investigation")
        op.drop_table("investigation")
