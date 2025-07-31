"""Add tox_doc_generated fields

Revision ID: a02ad79f6bbd
Revises: 8cdac474f9fd
Create Date: 2025-08-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a02ad79f6bbd'
down_revision = '8cdac474f9fd'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tox_doc_generated', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('tox_doc_generated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('tox_doc_generated_by', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_column('tox_doc_generated_by')
        batch_op.drop_column('tox_doc_generated_at')
        batch_op.drop_column('tox_doc_generated')