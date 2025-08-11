"""create investigations tables

Revision ID: a6b7865e0c6c
Revises: 
Create Date: 2025-08-11 10:48:00.267957

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6b7865e0c6c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'investigation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_number', sa.String(length=16), nullable=False),
        sa.Column('external_case_number', sa.String(length=64), nullable=True),
        sa.Column('other_identifier', sa.String(length=64), nullable=True),
        sa.Column('subject_name', sa.String(length=128), nullable=False),
        sa.Column('maiden_name', sa.String(length=128), nullable=True),
        sa.Column('investigation_type', sa.String(length=64), nullable=True),
        sa.Column('mother_name', sa.String(length=128), nullable=False),
        sa.Column('birth_place', sa.String(length=128), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=False),
        sa.Column('taj_number', sa.String(length=16), nullable=False),
        sa.Column('residence', sa.String(length=255), nullable=False),
        sa.Column('citizenship', sa.String(length=255), nullable=False),
        sa.Column('institution_name', sa.String(length=128), nullable=False),
        sa.Column('registration_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expert1_id', sa.Integer(), nullable=True),
        sa.Column('expert2_id', sa.Integer(), nullable=True),
        sa.Column('describer_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['expert1_id'], ['user.id']),
        sa.ForeignKeyConstraint(['expert2_id'], ['user.id']),
        sa.ForeignKeyConstraint(['describer_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number')
    )
    op.create_index('ix_investigation_case_number', 'investigation', ['case_number'])
    op.create_index('ix_investigation_subject_name', 'investigation', ['subject_name'])
    op.create_index('ix_investigation_institution_name', 'investigation', ['institution_name'])
    op.create_index('ix_investigation_taj_number', 'investigation', ['taj_number'])

    op.create_table(
        'investigation_note',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['user.id']),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'investigation_attachment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['user.id']),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'investigation_change_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investigation_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=64), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('edited_by', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['edited_by'], ['user.id']),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('investigation_change_log')
    op.drop_table('investigation_attachment')
    op.drop_table('investigation_note')
    op.drop_index('ix_investigation_taj_number', table_name='investigation')
    op.drop_index('ix_investigation_institution_name', table_name='investigation')
    op.drop_index('ix_investigation_subject_name', table_name='investigation')
    op.drop_index('ix_investigation_case_number', table_name='investigation')
    op.drop_table('investigation')