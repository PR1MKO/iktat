from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "examination_add_assignment_cols"
down_revision = "0001_initial_examination"  # keep your real previous rev id here
branch_labels = None
depends_on = None

def upgrade():
    # SQLite-friendly adds
    op.add_column(
        "investigation",
        sa.Column("assignment_type", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "investigation",
        sa.Column("assigned_expert_id", sa.Integer(), nullable=True)
    )

def downgrade():
    op.drop_column("investigation", "assigned_expert_id")
    op.drop_column("investigation", "assignment_type")
