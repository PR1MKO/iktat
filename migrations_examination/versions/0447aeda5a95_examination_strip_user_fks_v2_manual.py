"""examination: strip user FKs v2 (manual, SQLite-safe)"""

from alembic import op

# Keep these IDs exactly for this file
revision = "0447aeda5a95"
down_revision = "a1e8c3de0f9b"
branch_labels = None
depends_on = None


def upgrade():
    # Disable FK checks during rebuild
    op.execute("PRAGMA foreign_keys=OFF;")

    # -------------------------
    # investigation (drop all FKs; none we want to keep)
    # -------------------------
    op.execute(
        """
    ALTER TABLE investigation RENAME TO investigation_old;
    """
    )
    op.execute(
        """
    CREATE TABLE investigation (
        id INTEGER NOT NULL PRIMARY KEY,
        case_number VARCHAR(16) NOT NULL UNIQUE,
        external_case_number VARCHAR(64),
        other_identifier VARCHAR(64),
        subject_name VARCHAR(128) NOT NULL,
        maiden_name VARCHAR(128),
        investigation_type VARCHAR(64),
        mother_name VARCHAR(128) NOT NULL,
        birth_place VARCHAR(128) NOT NULL,
        birth_date DATE NOT NULL,
        taj_number VARCHAR(16) NOT NULL,
        residence VARCHAR(255) NOT NULL,
        citizenship VARCHAR(255) NOT NULL,
        institution_name VARCHAR(128) NOT NULL,
        registration_time DATETIME,
        deadline DATETIME,
        expert1_id INTEGER,
        expert2_id INTEGER,
        describer_id INTEGER,
        assignment_type VARCHAR(32),
        assigned_expert_id INTEGER
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation (
        id, case_number, external_case_number, other_identifier, subject_name, maiden_name,
        investigation_type, mother_name, birth_place, birth_date, taj_number, residence,
        citizenship, institution_name, registration_time, deadline, expert1_id, expert2_id,
        describer_id, assignment_type, assigned_expert_id
    )
    SELECT
        id, case_number, external_case_number, other_identifier, subject_name, maiden_name,
        investigation_type, mother_name, birth_place, birth_date, taj_number, residence,
        citizenship, institution_name, registration_time, deadline, expert1_id, expert2_id,
        describer_id, assignment_type, assigned_expert_id
    FROM investigation_old;
    """
    )
    op.execute("DROP TABLE investigation_old;")

    # -------------------------
    # investigation_attachment (keep ONLY FK to investigation(investigation_id))
    # -------------------------
    op.execute(
        "ALTER TABLE investigation_attachment RENAME TO investigation_attachment_old;"
    )
    op.execute(
        """
    CREATE TABLE investigation_attachment (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        filename VARCHAR(255) NOT NULL,
        category VARCHAR(64),
        uploaded_by INTEGER NOT NULL,
        uploaded_at DATETIME,
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_attachment (
        id, investigation_id, filename, category, uploaded_by, uploaded_at
    )
    SELECT id, investigation_id, filename, category, uploaded_by, uploaded_at
    FROM investigation_attachment_old;
    """
    )
    op.execute("DROP TABLE investigation_attachment_old;")

    # -------------------------
    # investigation_change_log (keep ONLY FK to investigation(investigation_id))
    # -------------------------
    op.execute(
        "ALTER TABLE investigation_change_log RENAME TO investigation_change_log_old;"
    )
    op.execute(
        """
    CREATE TABLE investigation_change_log (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        field_name VARCHAR(64) NOT NULL,
        old_value TEXT,
        new_value TEXT,
        edited_by INTEGER NOT NULL,
        timestamp DATETIME,
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_change_log (
        id, investigation_id, field_name, old_value, new_value, edited_by, timestamp
    )
    SELECT id, investigation_id, field_name, old_value, new_value, edited_by, timestamp
    FROM investigation_change_log_old;
    """
    )
    op.execute("DROP TABLE investigation_change_log_old;")

    # -------------------------
    # investigation_note (keep ONLY FK to investigation(investigation_id))
    # -------------------------
    op.execute("ALTER TABLE investigation_note RENAME TO investigation_note_old;")
    op.execute(
        """
    CREATE TABLE investigation_note (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        timestamp DATETIME,
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_note (
        id, investigation_id, author_id, text, timestamp
    )
    SELECT id, investigation_id, author_id, text, timestamp
    FROM investigation_note_old;
    """
    )
    op.execute("DROP TABLE investigation_note_old;")

    # Re-enable FK checks
    op.execute("PRAGMA foreign_keys=ON;")


def downgrade():
    # Best-effort reverse: reintroduce user FKs (will only work if a 'user' table exists here)
    op.execute("PRAGMA foreign_keys=OFF;")

    # investigation_note
    op.execute("ALTER TABLE investigation_note RENAME TO investigation_note_old;")
    op.execute(
        """
    CREATE TABLE investigation_note (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        timestamp DATETIME,
        FOREIGN KEY(author_id) REFERENCES user (id),
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_note
    SELECT id, investigation_id, author_id, text, timestamp
    FROM investigation_note_old;
    """
    )
    op.execute("DROP TABLE investigation_note_old;")

    # investigation_change_log
    op.execute(
        "ALTER TABLE investigation_change_log RENAME TO investigation_change_log_old;"
    )
    op.execute(
        """
    CREATE TABLE investigation_change_log (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        field_name VARCHAR(64) NOT NULL,
        old_value TEXT,
        new_value TEXT,
        edited_by INTEGER NOT NULL,
        timestamp DATETIME,
        FOREIGN KEY(edited_by) REFERENCES user (id),
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_change_log
    SELECT id, investigation_id, field_name, old_value, new_value, edited_by, timestamp
    FROM investigation_change_log_old;
    """
    )
    op.execute("DROP TABLE investigation_change_log_old;")

    # investigation_attachment
    op.execute(
        "ALTER TABLE investigation_attachment RENAME TO investigation_attachment_old;"
    )
    op.execute(
        """
    CREATE TABLE investigation_attachment (
        id INTEGER NOT NULL PRIMARY KEY,
        investigation_id INTEGER NOT NULL,
        filename VARCHAR(255) NOT NULL,
        category VARCHAR(64),
        uploaded_by INTEGER NOT NULL,
        uploaded_at DATETIME,
        FOREIGN KEY(uploaded_by) REFERENCES user (id),
        FOREIGN KEY(investigation_id) REFERENCES investigation (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation_attachment
    SELECT id, investigation_id, filename, category, uploaded_by, uploaded_at
    FROM investigation_attachment_old;
    """
    )
    op.execute("DROP TABLE investigation_attachment_old;")

    # investigation
    op.execute("ALTER TABLE investigation RENAME TO investigation_old;")
    op.execute(
        """
    CREATE TABLE investigation (
        id INTEGER NOT NULL PRIMARY KEY,
        case_number VARCHAR(16) NOT NULL UNIQUE,
        external_case_number VARCHAR(64),
        other_identifier VARCHAR(64),
        subject_name VARCHAR(128) NOT NULL,
        maiden_name VARCHAR(128),
        investigation_type VARCHAR(64),
        mother_name VARCHAR(128) NOT NULL,
        birth_place VARCHAR(128) NOT NULL,
        birth_date DATE NOT NULL,
        taj_number VARCHAR(16) NOT NULL,
        residence VARCHAR(255) NOT NULL,
        citizenship VARCHAR(255) NOT NULL,
        institution_name VARCHAR(128) NOT NULL,
        registration_time DATETIME,
        deadline DATETIME,
        expert1_id INTEGER,
        expert2_id INTEGER,
        describer_id INTEGER,
        assignment_type VARCHAR(32),
        assigned_expert_id INTEGER,
        FOREIGN KEY(describer_id) REFERENCES user (id),
        FOREIGN KEY(expert1_id) REFERENCES user (id),
        FOREIGN KEY(expert2_id) REFERENCES user (id)
    );
    """
    )
    op.execute(
        """
    INSERT INTO investigation (
        id, case_number, external_case_number, other_identifier, subject_name, maiden_name,
        investigation_type, mother_name, birth_place, birth_date, taj_number, residence,
        citizenship, institution_name, registration_time, deadline, expert1_id, expert2_id,
        describer_id, assignment_type, assigned_expert_id
    )
    SELECT
        id, case_number, external_case_number, other_identifier, subject_name, maiden_name,
        investigation_type, mother_name, birth_place, birth_date, taj_number, residence,
        citizenship, institution_name, registration_time, deadline, expert1_id, expert2_id,
        describer_id, assignment_type, assigned_expert_id
    FROM investigation_old;
    """
    )
    op.execute("DROP TABLE investigation_old;")

    op.execute("PRAGMA foreign_keys=ON;")
