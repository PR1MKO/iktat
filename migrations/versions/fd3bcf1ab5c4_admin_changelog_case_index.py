"""Add composite index for change log case lookup

Revision ID: fd3bcf1ab5c4
Revises: 39caa26b164c
Create Date: 2025-08-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = "fd3bcf1ab5c4"
down_revision = "69dd3c52d36f"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_change_log_case_id_ts"


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
    if not _table_exists("change_log"):
        return
    insp = sa.inspect(op.get_bind())
    existing = {idx["name"] for idx in insp.get_indexes("change_log")}
    if INDEX_NAME not in existing:
        op.create_index(INDEX_NAME, "change_log", ["case_id", "timestamp"])


def downgrade_main():
    if not _table_exists("change_log"):
        return
    insp = sa.inspect(op.get_bind())
    existing = {idx["name"] for idx in insp.get_indexes("change_log")}
    if INDEX_NAME in existing:
        op.drop_index(INDEX_NAME, table_name="change_log")


def upgrade_examination():
    # No-op for examination bind in this revision
    pass


def downgrade_examination():
    # No-op for examination bind in this revision
    pass
