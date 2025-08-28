# migrations/versions/e361b9f3fdb8_canonicalize_case_status_default.py
"""Canonicalize Case.status default to 'new' and ensure non-null (SQLite-safe)

Revision ID: e361b9f3fdb8
Revises: 147a352640ee
Create Date: 2025-08-27 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e361b9f3fdb8"
down_revision = "147a352640ee"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return table_name in insp.get_table_names()
    except Exception:
        return False


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return any(col["name"] == column_name for col in insp.get_columns(table_name))
    except Exception:
        return False


def upgrade():
    # Only act if this DB actually has the "case" table & "status" column.
    if not _has_table("case") or not _has_column("case", "status"):
        return

    # Backfill NULLs to canonical default (idempotent).
    op.execute('UPDATE "case" SET status = \'new\' WHERE status IS NULL')

    # Ensure NOT NULL + server_default using SQLite-safe batch alter.
    with op.batch_alter_table("case") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=32),
            nullable=False,
            server_default=sa.text("'new'"),
            existing_nullable=True,
        )


def downgrade():
    # Skip if table/column not present.
    if not _has_table("case") or not _has_column("case", "status"):
        return

    # Revert server_default to prior value ('beérkezett'); keep NOT NULL.
    with op.batch_alter_table("case") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.String(length=32),
            nullable=False,
            server_default=sa.text("'beérkezett'"),
            existing_nullable=False,
        )
