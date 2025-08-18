from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "b79a7cf96c00"
down_revision = "a0c2905147be"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("user")}
    if "full_name" not in cols:
        op.add_column("user", sa.Column("full_name", sa.String(length=128), nullable=True))
    # else: column already present; no-op

def downgrade():
    # drop if exists (Alembic will handle SQLite via batch mode if configured)
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("user")}
    if "full_name" in cols:
        op.drop_column("user", "full_name")
