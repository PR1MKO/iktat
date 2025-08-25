"""normalize case status literals"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e1f5305a2b1d'
down_revision = 'f2ca12fa098a'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("UPDATE case SET status='lezárt' WHERE status IN ('lezárva','lejárt')")

def downgrade():
    # no-op; data cleanup not easily reversible
    pass