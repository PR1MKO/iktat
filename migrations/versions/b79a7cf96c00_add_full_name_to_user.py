from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '<KEEP_THE_GENERATED_REV_ID>'
down_revision = '<KEEP_THE_GENERATED_DOWN_REV>'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('full_name', sa.String(length=128), nullable=True))

def downgrade():
    op.drop_column('user', 'full_name')
