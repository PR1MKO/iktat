"""drop user foreign keys (SQLite-safe via batch recreate)"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1e8c3de0f9b"
down_revision = "067b02161497"
branch_labels = None
depends_on = None


def _recreate_without_cross_user_fks():
    """
    Recreate tables with reflect_kwargs={'resolve_fks': False} so Alembic
    does NOT try to resolve foreign keys to the non-existent 'user' table
    in this database. Then explicitly re-add ONLY the intra-exam FKs that
    should remain (those pointing to 'investigation(id)').
    """

    # 1) investigation: only had FKs to 'user' → recreate and keep as-is (no FKs to keep)
    with op.batch_alter_table(
        "investigation",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        pass  # table recreated without any FKs; integer ID columns remain

    # 2) investigation_attachment: keep FK to investigation(investigation_id), drop 'user'
    with op.batch_alter_table(
        "investigation_attachment",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(
            "fk_investigation_attachment_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )
        # note: do NOT recreate uploaded_by -> user

    # 3) investigation_change_log: keep FK to investigation(investigation_id), drop 'user'
    with op.batch_alter_table(
        "investigation_change_log",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(
            "fk_investigation_change_log_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )
        # note: do NOT recreate edited_by -> user

    # 4) investigation_note: keep FK to investigation(investigation_id), drop 'user'
    with op.batch_alter_table(
        "investigation_note",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(
            "fk_investigation_note_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )
        # note: do NOT recreate author_id -> user


def upgrade():
    _recreate_without_cross_user_fks()


def downgrade():
    # Best-effort downgrade (recreate user FKs if someone really wants them back).
    # WARNING: This assumes a 'user' table exists in this DB on downgrade, which it usually won't.
    with op.batch_alter_table(
        "investigation",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        # re-add user FKs (names optional in SQLite)
        batch.create_foreign_key(None, "user", ["expert1_id"], ["id"])
        batch.create_foreign_key(None, "user", ["expert2_id"], ["id"])
        batch.create_foreign_key(None, "user", ["describer_id"], ["id"])

    with op.batch_alter_table(
        "investigation_attachment",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(None, "user", ["uploaded_by"], ["id"])
        batch.create_foreign_key(
            "fk_investigation_attachment_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )

    with op.batch_alter_table(
        "investigation_change_log",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(None, "user", ["edited_by"], ["id"])
        batch.create_foreign_key(
            "fk_investigation_change_log_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )

    with op.batch_alter_table(
        "investigation_note",
        recreate="always",
        reflect_kwargs={"resolve_fks": False},
    ) as batch:
        batch.create_foreign_key(None, "user", ["author_id"], ["id"])
        batch.create_foreign_key(
            "fk_investigation_note_investigation_id",
            "investigation",
            ["investigation_id"],
            ["id"],
        )
