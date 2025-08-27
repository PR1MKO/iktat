import re
import pathlib


def test_env_sets_tag_and_batch(app):
    with app.app_context():
        from importlib import import_module

        env = import_module("migrations.env")
        assert hasattr(env, "run_migrations_online")
        assert hasattr(env, "include_object")


def test_env_version_locations_present():
    from alembic.config import Config

    Config()  # placeholder to mirror env expectations
    from migrations import env as env_mod

    val = env_mod.config.get_main_option("version_locations")
    assert "migrations/versions" in val
    assert "migrations_examination/versions" in val


def test_cross_bind_revisions_gated():
    a = pathlib.Path(
        "migrations/versions/a0c2905147be_add_examinationcase_table.py"
    ).read_text(encoding="utf-8")
    b = pathlib.Path(
        "migrations/versions/f2ca12fa098a_drop_legacy_examination_case_from_core.py"
    ).read_text(encoding="utf-8")
    assert "context.get_tag_argument()" in a
    assert "context.get_tag_argument()" in b


def test_render_as_batch_asserted():
    s = pathlib.Path("migrations/env.py").read_text(encoding="utf-8")
    # offline configure must pass render_as_batch and tag
    assert re.search(r"render_as_batch\s*=\s*render_as_batch", s)
    assert re.search(r"tag\s*=\s*bind_key", s)
    # online configure must pass render_as_batch and tag
    assert re.search(r"render_as_batch\s*=\s*is_sqlite", s)
    assert re.search(r"tag\s*=\s*bind_key", s)
