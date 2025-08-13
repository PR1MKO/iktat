from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_investigation_assignment_type'
down_revision = '0001_initial_examination'
branch_labels = None
depends_on = None


def upgrade():
    assignment_type_enum = sa.Enum('INTEZETI', 'SZAKÉRTŐI', name='assignment_type')
    assignment_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'investigation',
        sa.Column('assignment_type', assignment_type_enum, nullable=False, server_default='INTEZETI')
    )
    op.add_column(
        'investigation',
        sa.Column('assigned_expert_id', sa.Integer(), nullable=True)
    )
    op.create_index('ix_investigation_assigned_expert_id', 'investigation', ['assigned_expert_id'])
    op.alter_column('investigation', 'assignment_type', server_default=None)


def downgrade():
    op.drop_index('ix_investigation_assigned_expert_id', table_name='investigation')
    op.drop_column('investigation', 'assigned_expert_id')
    op.drop_column('investigation', 'assignment_type')

    assignment_type_enum = sa.Enum('INTEZETI', 'SZAKÉRTŐI', name='assignment_type')
    assignment_type_enum.drop(op.get_bind(), checkfirst=True)