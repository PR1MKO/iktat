"""add cookie_notice_ack_at to user"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import NoSuchTableError

# revision identifiers, used by Alembic.
revision = "b1f7a4b2b9c8"
down_revision = "e361b9f3fdb8"
branch_labels = None
depends_on = None


def _table_exists(insp, table_name: str) -> bool:
    has = getattr(insp, "has_table", None)
    if callable(has):
        return insp.has_table(table_name)
    try:
        insp.get_columns(table_name)
        return True
    except NoSuchTableError:
        return False


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if not _table_exists(insp, "user"):
        return

    cols = {c["name"] for c in insp.get_columns("user")}
    if "cookie_notice_ack_at" not in cols:
        with op.batch_alter_table("user", schema=None) as batch:
            batch.add_column(
                sa.Column(
                    "cookie_notice_ack_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if not _table_exists(insp, "user"):
        return

    cols = {c["name"] for c in insp.get_columns("user")}
    if "cookie_notice_ack_at" in cols:
        with op.batch_alter_table("user", schema=None) as batch:
            batch.drop_column("cookie_notice_ack_at")
