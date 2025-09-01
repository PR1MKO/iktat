import re
from pathlib import Path


def test_env_has_render_as_batch():
    p = Path("migrations") / "env.py"
    s = p.read_text(encoding="utf-8")
    assert "render_as_batch" in s
    assert re.search(r"context\.configure\([^)]*render_as_batch", s)


def test_flagged_migration_is_batched():
    files = list(
        Path("migrations/versions").glob("b79a7cf96c00*_add_full_name_to_user.py")
    )
    assert files, "flagged migration file not found"
    s = files[0].read_text(encoding="utf-8")
    assert "batch_alter_table" in s
    assert "add_column" in s and "drop_column" in s
