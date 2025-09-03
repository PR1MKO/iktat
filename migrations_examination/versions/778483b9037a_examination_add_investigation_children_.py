"""examination: add missing cols on investigation, then children + indexes + named unique constraint

Revision ID: a1b2c3d4e5f6
Revises: 6f2c9a1e3b21
Create Date: 2025-09-03 14:58:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# Revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "6f2c9a1e3b21"
branch_labels = None
depends_on = None


def _has_column(inspector: Inspector, table: str, column: str) -> bool:
    cols = inspector.get_columns(table)
    return any(c["name"] == column for c in cols)


def upgrade() -> None:
    # --- SAFETY: clean up any stale scratch table from a prior failed batch ---
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_investigation")

    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- 1) Ensure investigation has all model columns (idempotent add_column) ---
    # These ADD COLUMN ops are SQLite-native and do not require table recreate.
    add_cols = [
        ("maiden_name", sa.String(128), None),
        ("investigation_type", sa.String(64), None),
        ("birth_place", sa.String(128), None),
        ("birth_date", sa.Date(), None),
        ("taj_number", sa.String(16), None),
        ("residence", sa.String(255), None),
        ("citizenship", sa.String(255), None),
        ("institution_name", sa.String(128), None),
        ("assignment_type", sa.String(64), sa.text("'INTEZETI'")),
        ("assigned_expert_id", sa.Integer(), None),
        ("expert1_id", sa.Integer(), None),
        ("expert2_id", sa.Integer(), None),
        ("describer_id", sa.Integer(), None),
        ("deadline", sa.DateTime(timezone=True), None),
    ]

    for name, coltype, server_default in add_cols:
        if not _has_column(insp, "investigation", name):
            op.add_column(
                "investigation",
                sa.Column(name, coltype, server_default=server_default),
            )
            # Drop the default after creation if we set one just to satisfy NOT NULL / default
            if server_default is not None:
                with op.batch_alter_table("investigation") as batch:
                    batch.alter_column(name, server_default=None)

    # mother_name / registration_time may exist and be nullable in DB; we won't
    # force NOT NULL on SQLite here to avoid data issues. The model enforces at app level.

    # --- 2) Replace legacy unique *index* with a named UniqueConstraint ---
    # First, remove the legacy unique index if it exists (best-effort).
    try:
        op.drop_index("ux_investigation_case_number", table_name="investigation")
    except Exception:
        pass

    # Ensure no stale scratch table from a previous partial batch run
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_investigation")

    # Now create the named UniqueConstraint via batch (SQLite-safe)
    with op.batch_alter_table("investigation") as batch:
        # If the constraint already exists, this is a no-op (SQLite doesn’t track names well,
        # but Alembic will just recreate the table with the constraint in the new DDL).
        batch.create_unique_constraint("ux_investigation_case_number", ["case_number"])

    # --- 3) New secondary indexes on investigation (idempotent) ---
    def _create_index_if_missing(ix_name: str, table: str, cols: list[str]) -> None:
        # SQLite lacks "IF NOT EXISTS" for indexes in older versions; just best-effort.
        try:
            op.create_index(ix_name, table, cols, unique=False)
        except Exception:
            pass

    _create_index_if_missing(
        "ix_investigation_assigned_expert_id", "investigation", ["assigned_expert_id"]
    )
    _create_index_if_missing(
        "ix_investigation_describer_id", "investigation", ["describer_id"]
    )
    _create_index_if_missing(
        "ix_investigation_expert1_id", "investigation", ["expert1_id"]
    )
    _create_index_if_missing(
        "ix_investigation_expert2_id", "investigation", ["expert2_id"]
    )
    _create_index_if_missing(
        "ix_investigation_institution_name", "investigation", ["institution_name"]
    )
    _create_index_if_missing(
        "ix_investigation_subject_name", "investigation", ["subject_name"]
    )
    _create_index_if_missing(
        "ix_investigation_taj_number", "investigation", ["taj_number"]
    )

    # --- 4) Child tables (note, attachment, change_log) + their indexes ---
    # Create tables only if they don't exist (simple try/except for idempotency).
    try:
        op.create_table(
            "investigation_note",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "investigation_id",
                sa.Integer(),
                sa.ForeignKey("investigation.id"),
                nullable=False,
            ),
            sa.Column("author_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        )
    except Exception:
        pass
    _create_index_if_missing(
        "ix_investigation_note_author_id", "investigation_note", ["author_id"]
    )

    try:
        op.create_table(
            "investigation_attachment",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "investigation_id",
                sa.Integer(),
                sa.ForeignKey("investigation.id"),
                nullable=False,
            ),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("uploaded_by", sa.Integer(), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        )
    except Exception:
        pass
    _create_index_if_missing(
        "ix_investigation_attachment_uploaded_by",
        "investigation_attachment",
        ["uploaded_by"],
    )

    try:
        op.create_table(
            "investigation_change_log",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "investigation_id",
                sa.Integer(),
                sa.ForeignKey("investigation.id"),
                nullable=False,
            ),
            sa.Column("field_name", sa.String(length=64), nullable=False),
            sa.Column("old_value", sa.Text()),
            sa.Column("new_value", sa.Text()),
            sa.Column("edited_by", sa.Integer(), nullable=False),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        )
    except Exception:
        pass
    _create_index_if_missing(
        "ix_investigation_change_log_edited_by",
        "investigation_change_log",
        ["edited_by"],
    )


def downgrade() -> None:
    # Drop child tables (FK dependents) first
    for ix, tbl in [
        ("ix_investigation_change_log_edited_by", "investigation_change_log"),
        ("ix_investigation_attachment_uploaded_by", "investigation_attachment"),
        ("ix_investigation_note_author_id", "investigation_note"),
    ]:
        try:
            op.drop_index(ix, table_name=tbl)
        except Exception:
            pass
    for tbl in [
        "investigation_change_log",
        "investigation_attachment",
        "investigation_note",
    ]:
        try:
            op.drop_table(tbl)
        except Exception:
            pass

    # Drop the added investigation indexes
    for ix in [
        "ix_investigation_assigned_expert_id",
        "ix_investigation_describer_id",
        "ix_investigation_expert1_id",
        "ix_investigation_expert2_id",
        "ix_investigation_institution_name",
        "ix_investigation_subject_name",
        "ix_investigation_taj_number",
    ]:
        try:
            op.drop_index(ix, table_name="investigation")
        except Exception:
            pass

    # Replace the named UniqueConstraint back to unique index for downgrade symmetry
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_investigation")
    try:
        with op.batch_alter_table("investigation") as batch:
            batch.drop_constraint("ux_investigation_case_number", type_="unique")
    except Exception:
        pass
    try:
        op.create_index(
            "ux_investigation_case_number",
            "investigation",
            ["case_number"],
            unique=True,
        )
    except Exception:
        pass
