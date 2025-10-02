"""Add composite index for investigation change log lookup

Revision ID: 48c6473d06a3
Revises: c4d79b86fe55
Create Date: 2025-08-15 12:05:00.000000

"""

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = "48c6473d06a3"
down_revision = "c4d79b86fe55"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_investigation_change_log_inv_id_ts"


def _is_examination_bind() -> bool:
    tag = context.get_tag_argument()
    if tag and tag != "examination":
        return False
    try:
        x_args = context.get_x_argument(as_dictionary=True)
    except Exception:  # pragma: no cover - optional in offline runs
        x_args = {}
    bind = x_args.get("bind") or x_args.get("bind_key")
    if bind and bind != "examination":
        return False
    if not tag and not bind:
        return False
    return True


def upgrade() -> None:
    if not _is_examination_bind():
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "investigation_change_log" not in inspector.get_table_names():
        return

    existing = {
        idx["name"] for idx in inspector.get_indexes("investigation_change_log")
    }
    if INDEX_NAME not in existing:
        op.create_index(
            INDEX_NAME,
            "investigation_change_log",
            ["investigation_id", "timestamp"],
        )


def downgrade() -> None:
    if not _is_examination_bind():
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "investigation_change_log" not in inspector.get_table_names():
        return

    existing = {
        idx["name"] for idx in inspector.get_indexes("investigation_change_log")
    }
    if INDEX_NAME in existing:
        op.drop_index(INDEX_NAME, table_name="investigation_change_log")
