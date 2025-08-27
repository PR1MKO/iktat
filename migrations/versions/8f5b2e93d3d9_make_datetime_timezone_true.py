"""make datetime timezone true

Revision ID: 8f5b2e93d3d9
Revises: a0c2905147be
Create Date: 2025-08-07 13:36:31.799129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f5b2e93d3d9'
down_revision = 'a0c2905147be'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    with op.batch_alter_table('case') as batch_op:
        batch_op.alter_column('certificate_generated_at', type_=sa.DateTime(timezone=True))
        batch_op.alter_column('tox_doc_generated_at', type_=sa.DateTime(timezone=True))
    with op.batch_alter_table('uploaded_file') as batch_op:
        batch_op.alter_column('upload_time', type_=sa.DateTime(timezone=True))
    with op.batch_alter_table('idempotency_token') as batch_op:
        batch_op.alter_column('created_at', type_=sa.DateTime(timezone=True))


def downgrade():
    # Keep timezone awareness on downgrade to avoid reintroducing naive columns.
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        return
    with op.batch_alter_table('case') as batch_op:
        batch_op.alter_column('certificate_generated_at', type_=sa.DateTime(timezone=True))
        batch_op.alter_column('tox_doc_generated_at', type_=sa.DateTime(timezone=True))
    with op.batch_alter_table('uploaded_file') as batch_op:
        batch_op.alter_column('upload_time', type_=sa.DateTime(timezone=True))
    with op.batch_alter_table('idempotency_token') as batch_op:
        batch_op.alter_column('created_at', type_=sa.DateTime(timezone=True))