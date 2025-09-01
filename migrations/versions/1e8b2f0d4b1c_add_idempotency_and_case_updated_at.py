"""Add IdempotencyToken table and Case.updated_at

Revision ID: 1e8b2f0d4b1c
Revises: f2ca12fa098a
Create Date: 2025-09-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "1e8b2f0d4b1c"
down_revision = "f2ca12fa098a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idempotency_token",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["case.id"]),
        sa.UniqueConstraint("key"),
    )
    op.create_index(
        "ix_idempotency_token_route_user_case_created_at",
        "idempotency_token",
        ["route", "user_id", "case_id", "created_at"],
    )

    with op.batch_alter_table("case") as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=func.now(),
                nullable=False,
            )
        )


def downgrade():
    with op.batch_alter_table("case") as batch_op:
        batch_op.drop_column("updated_at")

    op.drop_index(
        "ix_idempotency_token_route_user_case_created_at",
        table_name="idempotency_token",
    )
    op.drop_table("idempotency_token")
