"""Add Case model

Revision ID: f02f2c72c9b9
Revises: 16a2ed153d7e
Create Date: 2025-06-11 12:38:01.521919

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f02f2c72c9b9'
down_revision = '16a2ed153d7e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('case',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('case_number', sa.String(length=32), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('assigned_office', sa.String(length=64), nullable=True),
    sa.Column('assigned_signatory', sa.String(length=64), nullable=True),
    sa.Column('assigned_pathologist', sa.String(length=64), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('case_number')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('case')
    # ### end Alembic commands ###
