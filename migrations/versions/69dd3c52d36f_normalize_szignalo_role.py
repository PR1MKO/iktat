"""normalize szignalo role

Revision ID: 69dd3c52d36f
Revises: c1c2b7240f6a
Create Date: 2025-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op, context

# revision identifiers, used by Alembic.
revision = "69dd3c52d36f"
down_revision = "c1c2b7240f6a"
branch_labels = None
depends_on = None


def _current_bind():
    tag = context.get_tag_argument()
    if tag:
        return tag
    try:
        x = context.get_x_argument(as_dictionary=True)
        return x.get("bind") or x.get("bind_key")
    except Exception:
        return None


def _table_exists(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, col: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == col for c in insp.get_columns(table))


def upgrade():
    b = _current_bind()
    if b in ("default", "main", None):
        upgrade_main()
    elif b == "examination":
        upgrade_examination()


def downgrade():
    b = _current_bind()
    if b in ("default", "main", None):
        downgrade_main()
    elif b == "examination":
        downgrade_examination()


def upgrade_main():
    if _table_exists("user") and _has_column("user", "role"):
        # Idempotent data migration: only rows with role='szig' will change.
        op.execute(
            sa.text('UPDATE "user" SET role = :new WHERE role = :old').bindparams(
                new="szignáló", old="szig"
            )
        )


def downgrade_main():
    if _table_exists("user") and _has_column("user", "role"):
        # Reverse the normalization.
        op.execute(
            sa.text('UPDATE "user" SET role = :old WHERE role = :new').bindparams(
                new="szignáló", old="szig"
            )
        )


def upgrade_examination():
    pass


def downgrade_examination():
    pass
