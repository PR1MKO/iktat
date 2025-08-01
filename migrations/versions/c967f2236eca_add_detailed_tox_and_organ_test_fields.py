"""Add detailed tox and organ test fields

Revision ID: c967f2236eca
Revises: 9d325130fcd5
Create Date: 2025-07-02 12:20:41.058606

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c967f2236eca'
down_revision = '9d325130fcd5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.add_column(sa.Column('alkohol_ver', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('alkohol_vizelet', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('alkohol_liquor', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('egyeb_alkohol', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('tox_gyogyszer_ver', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_gyogyszer_vizelet', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_gyogyszer_gyomor', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_gyogyszer_maj', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_kabitoszer_ver', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_kabitoszer_vizelet', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_cpk', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_szarazanyag', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_diatoma', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('tox_co', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('egyeb_tox', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('sziv_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('sziv_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('tudo_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('tudo_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('maj_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('maj_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('vese_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('vese_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('agy_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('agy_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mellekvese_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('mellekvese_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('pajzsmirigy_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('pajzsmirigy_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('hasnyalmirigy_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('hasnyalmirigy_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('lep_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('lep_immun', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('egyeb_szerv', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('egyeb_szerv_spec', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('egyeb_szerv_immun', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_column('egyeb_szerv_immun')
        batch_op.drop_column('egyeb_szerv_spec')
        batch_op.drop_column('egyeb_szerv')
        batch_op.drop_column('lep_immun')
        batch_op.drop_column('lep_spec')
        batch_op.drop_column('hasnyalmirigy_immun')
        batch_op.drop_column('hasnyalmirigy_spec')
        batch_op.drop_column('pajzsmirigy_immun')
        batch_op.drop_column('pajzsmirigy_spec')
        batch_op.drop_column('mellekvese_immun')
        batch_op.drop_column('mellekvese_spec')
        batch_op.drop_column('agy_immun')
        batch_op.drop_column('agy_spec')
        batch_op.drop_column('vese_immun')
        batch_op.drop_column('vese_spec')
        batch_op.drop_column('maj_immun')
        batch_op.drop_column('maj_spec')
        batch_op.drop_column('tudo_immun')
        batch_op.drop_column('tudo_spec')
        batch_op.drop_column('sziv_immun')
        batch_op.drop_column('sziv_spec')
        batch_op.drop_column('egyeb_tox')
        batch_op.drop_column('tox_co')
        batch_op.drop_column('tox_diatoma')
        batch_op.drop_column('tox_szarazanyag')
        batch_op.drop_column('tox_cpk')
        batch_op.drop_column('tox_kabitoszer_vizelet')
        batch_op.drop_column('tox_kabitoszer_ver')
        batch_op.drop_column('tox_gyogyszer_maj')
        batch_op.drop_column('tox_gyogyszer_gyomor')
        batch_op.drop_column('tox_gyogyszer_vizelet')
        batch_op.drop_column('tox_gyogyszer_ver')
        batch_op.drop_column('egyeb_alkohol')
        batch_op.drop_column('alkohol_liquor')
        batch_op.drop_column('alkohol_vizelet')
        batch_op.drop_column('alkohol_ver')

    # ### end Alembic commands ###
