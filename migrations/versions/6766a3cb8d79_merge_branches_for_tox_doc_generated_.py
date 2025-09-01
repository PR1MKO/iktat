"""Merge branches for tox_doc_generated fields

Revision ID: 6766a3cb8d79
Revises: 39caa26b164c, a02ad79f6bbd
Create Date: 2025-07-31 12:50:43.525991

"""

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "6766a3cb8d79"
down_revision = ("39caa26b164c", "a02ad79f6bbd")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
