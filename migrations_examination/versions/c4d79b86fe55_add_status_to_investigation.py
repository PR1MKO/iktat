"""Add status column to investigation (examination bind)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# Revision identifiers, used by Alembic.
revision = "c4d79b86fe55"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_TABLE_NAME = "investigation"
_COLUMN_NAME = "status"
_DEFAULT = sa.text("'beérkezett'")


def _get_inspector() -> Inspector:
    bind = op.get_bind()
    return sa.inspect(bind)


def _table_exists(inspector: Inspector, table: str) -> bool:
    try:
        return table in inspector.get_table_names()
    except Exception:  # noqa: BLE001
        return False


def _column_exists(inspector: Inspector, table: str, column: str) -> bool:
    try:
        return any(col["name"] == column for col in inspector.get_columns(table))
    except Exception:  # noqa: BLE001
        return False


def upgrade() -> None:
    inspector = _get_inspector()
    if not _table_exists(inspector, _TABLE_NAME):
        return
    if _column_exists(inspector, _TABLE_NAME, _COLUMN_NAME):
        return

    op.execute("DROP TABLE IF EXISTS _alembic_tmp_investigation")

    with op.batch_alter_table(_TABLE_NAME) as batch:
        batch.add_column(
            sa.Column(
                _COLUMN_NAME,
                sa.String(length=32),
                nullable=False,
                server_default=_DEFAULT,
            )
        )


def downgrade() -> None:
    inspector = _get_inspector()
    if not _table_exists(inspector, _TABLE_NAME):
        return
    if not _column_exists(inspector, _TABLE_NAME, _COLUMN_NAME):
        return

    op.execute("DROP TABLE IF EXISTS _alembic_tmp_investigation")

    with op.batch_alter_table(_TABLE_NAME) as batch:
        batch.drop_column(_COLUMN_NAME)
