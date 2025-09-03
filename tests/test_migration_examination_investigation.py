import pathlib

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app import db


def _upgrade_examination(app, revision="6f2c9a1e3b21"):
    cfg = Config(str(pathlib.Path("migrations_examination/alembic.ini")))
    cfg.set_main_option("script_location", "migrations_examination")
    with app.app_context():
        command.upgrade(cfg, revision)


def _examination_engine(app):
    return db.engines["examination"]


def _reset_examination_db(app):
    eng = _examination_engine(app)
    with app.app_context():
        db.drop_all(bind_key="examination")
        with eng.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version_examination"))


def test_investigation_table_exists_on_examination(app):
    eng = _examination_engine(app)
    _reset_examination_db(app)
    _upgrade_examination(app)
    insp = sa.inspect(eng)
    assert "investigation" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("investigation")}
    assert {
        "id",
        "case_number",
        "external_case_number",
        "other_identifier",
        "subject_name",
        "mother_name",
        "registration_time",
    } <= cols


def test_case_number_unique_index_present(app):
    eng = _examination_engine(app)
    _reset_examination_db(app)
    _upgrade_examination(app)
    insp = sa.inspect(eng)
    idxs = insp.get_indexes("investigation")
    assert any(
        ix.get("unique") and ix.get("column_names") == ["case_number"] for ix in idxs
    )
