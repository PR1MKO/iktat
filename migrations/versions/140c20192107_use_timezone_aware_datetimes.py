"""use timezone aware datetimes

Revision ID: 140c20192107
Revises: 04dbfd4b792c
Create Date: 2025-07-11 11:10:21.562919

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "140c20192107"
down_revision = "04dbfd4b792c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case") as batch_op:
        batch_op.alter_column("registration_time", type_=sa.DateTime(timezone=True))
        batch_op.alter_column("deadline", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("timestamp", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("change_log") as batch_op:
        batch_op.alter_column("timestamp", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("uploaded_file") as batch_op:
        batch_op.alter_column("upload_time", type_=sa.DateTime(timezone=True))


def downgrade():
    # Preserve tz-aware columns on downgrade per project policy
    with op.batch_alter_table("case") as batch_op:
        batch_op.alter_column("registration_time", type_=sa.DateTime(timezone=True))
        batch_op.alter_column("deadline", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("timestamp", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("change_log") as batch_op:
        batch_op.alter_column("timestamp", type_=sa.DateTime(timezone=True))

    with op.batch_alter_table("uploaded_file") as batch_op:
        batch_op.alter_column("upload_time", type_=sa.DateTime(timezone=True))
