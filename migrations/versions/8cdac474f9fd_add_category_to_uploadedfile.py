"""Add category to UploadedFile

Revision ID: 8cdac474f9fd
Revises: 4c9783535cda
Create Date: 2025-07-30 09:53:12.187485

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8cdac474f9fd'
down_revision = '4c9783535cda'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('uploaded_file', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('category', sa.String(length=50), nullable=False, server_default='egyéb')
        )

def downgrade():
    with op.batch_alter_table('uploaded_file', schema=None) as batch_op:
        batch_op.drop_column('category')

    # ### end Alembic commands ###