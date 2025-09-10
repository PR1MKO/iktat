"""drop default on UploadedFile.category

Revision ID: c1c2b7240f6a
Revises: b1f7a4b2b9c8
Create Date: 2025-09-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision = "c1c2b7240f6a"
down_revision = "b1f7a4b2b9c8"
branch_labels = None
depends_on = None


def _current_bind() -> str | None:
    """Return the active bind key ('default' or 'examination') if provided by env.py."""
    tag = context.get_tag_argument()
    if tag:
        return tag
    try:
        x = context.get_x_argument(as_dictionary=True)  # EnvironmentContext API
        return x.get("bind") or x.get("bind_key")
    except Exception:
        return None  # env.py didn't pass args


def _table_exists(name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in insp.get_table_names()


def upgrade():
    b = _current_bind()

    # Our env.py sets tag=bind_key ("default" for main, "examination" for the bind)
    if b == "examination":
        upgrade_examination()
    elif b in ("default", "main", None):
        # Treat None as main in case tag is unavailable
        upgrade_main()
    else:
        # Unknown bind: last-resort inference
        if _table_exists("uploaded_file"):
            upgrade_main()


def downgrade():
    b = _current_bind()

    if b == "examination":
        downgrade_examination()
    elif b in ("default", "main", None):
        downgrade_main()
    else:
        if _table_exists("uploaded_file"):
            downgrade_main()


def upgrade_main():
    with op.batch_alter_table("uploaded_file", schema=None) as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.String(length=50),
            existing_nullable=False,
            server_default=None,  # drop default
        )


def downgrade_main():
    with op.batch_alter_table("uploaded_file", schema=None) as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.String(length=50),
            existing_nullable=False,
            server_default="egyéb",
        )


def upgrade_examination():
    # No-op: 'uploaded_file' table does not exist on the 'examination' bind
    pass


def downgrade_examination():
    # No-op
    pass
