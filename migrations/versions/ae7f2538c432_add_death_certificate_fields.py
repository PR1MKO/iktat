"""Add death certificate fields to Case

Revision ID: ae7f2538c432
Revises: 8c0438cc3f16
Create Date: 2025-08-30 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ae7f2538c432"
down_revision = "8c0438cc3f16"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("halalt_megallap_pathologus", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("halalt_megallap_kezeloorvos", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("halalt_megallap_mas_orvos", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(sa.Column("boncolas_tortent", sa.Boolean(), nullable=True))
        batch_op.add_column(
            sa.Column("varhato_tovabbi_vizsgalat", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kozvetlen_halalok", sa.String(length=256), nullable=True)
        )
        batch_op.add_column(
            sa.Column("kozvetlen_halalok_ido", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("alapbetegseg_szovodmenyei", sa.String(length=256), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "alapbetegseg_szovodmenyei_ido", sa.String(length=64), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("alapbetegseg", sa.String(length=256), nullable=True)
        )
        batch_op.add_column(
            sa.Column("alapbetegseg_ido", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(sa.Column("kiserobetegsegek", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("case", schema=None) as batch_op:
        batch_op.drop_column("kiserobetegsegek")
        batch_op.drop_column("alapbetegseg_ido")
        batch_op.drop_column("alapbetegseg")
        batch_op.drop_column("alapbetegseg_szovodmenyei_ido")
        batch_op.drop_column("alapbetegseg_szovodmenyei")
        batch_op.drop_column("kozvetlen_halalok_ido")
        batch_op.drop_column("kozvetlen_halalok")
        batch_op.drop_column("varhato_tovabbi_vizsgalat")
        batch_op.drop_column("boncolas_tortent")
        batch_op.drop_column("halalt_megallap_mas_orvos")
        batch_op.drop_column("halalt_megallap_kezeloorvos")
        batch_op.drop_column("halalt_megallap_pathologus")
