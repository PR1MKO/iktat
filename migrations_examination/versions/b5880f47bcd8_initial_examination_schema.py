"""initial examination schema"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_examination"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investigation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_number", sa.String(length=16), nullable=False),
        sa.Column("external_case_number", sa.String(length=64)),
        sa.Column("other_identifier", sa.String(length=64)),
        sa.Column("subject_name", sa.String(length=128), nullable=False),
        sa.Column("maiden_name", sa.String(length=128)),
        sa.Column("investigation_type", sa.String(length=64)),
        sa.Column("mother_name", sa.String(length=128), nullable=False),
        sa.Column("birth_place", sa.String(length=128), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("taj_number", sa.String(length=16), nullable=False),
        sa.Column("residence", sa.String(length=255), nullable=False),
        sa.Column("citizenship", sa.String(length=255), nullable=False),
        sa.Column("institution_name", sa.String(length=128), nullable=False),
        sa.Column("registration_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("expert1_id", sa.Integer(), nullable=True),
        sa.Column("expert2_id", sa.Integer(), nullable=True),
        sa.Column("describer_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("case_number", name="uq_investigation_case_number"),
    )
    op.create_index("ix_investigation_expert1", "investigation", ["expert1_id"])
    op.create_index("ix_investigation_expert2", "investigation", ["expert2_id"])
    op.create_index("ix_investigation_describer", "investigation", ["describer_id"])

    op.create_table(
        "investigation_note",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.Integer(),
            sa.ForeignKey("investigation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_investigation_note_author", "investigation_note", ["author_id"])

    op.create_table(
        "investigation_attachment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.Integer(),
            sa.ForeignKey("investigation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_investigation_attachment_uploaded_by",
        "investigation_attachment",
        ["uploaded_by"],
    )

    op.create_table(
        "investigation_change_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.Integer(),
            sa.ForeignKey("investigation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.Text()),
        sa.Column("new_value", sa.Text()),
        sa.Column("edited_by", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_investigation_change_log_edited_by",
        "investigation_change_log",
        ["edited_by"],
    )


def downgrade():
    op.drop_index(
        "ix_investigation_change_log_edited_by", table_name="investigation_change_log"
    )
    op.drop_table("investigation_change_log")

    op.drop_index(
        "ix_investigation_attachment_uploaded_by", table_name="investigation_attachment"
    )
    op.drop_table("investigation_attachment")

    op.drop_index("ix_investigation_note_author", table_name="investigation_note")
    op.drop_table("investigation_note")

    op.drop_index("ix_investigation_describer", table_name="investigation")
    op.drop_index("ix_investigation_expert2", table_name="investigation")
    op.drop_index("ix_investigation_expert1", table_name="investigation")
    op.drop_table("investigation")
