"""normalize case status literals

Revision ID: e1f5305a2b1d
Revises: f2ca12fa098a
Create Date: 2025-08-25 11:33:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "e1f5305a2b1d"
down_revision = "f2ca12fa098a"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite needs the "case" table to be quoted
    conn = op.get_bind()
    # Map both old forms -> canonical "lezárt"
    conn.execute(
        text('UPDATE "case" SET status = :new WHERE status IN (:a, :b)').bindparams(
            new="lezárt", a="lezárva", b="lejárt"
        )
    )


def downgrade():
    # Best-effort: turn "lezárt" back to "lezárva" if it used to be either
    conn = op.get_bind()
    conn.execute(
        text('UPDATE "case" SET status = :old WHERE status = :new').bindparams(
            old="lezárva", new="lezárt"
        )
    )
