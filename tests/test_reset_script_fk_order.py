import re
from pathlib import Path


def test_reset_script_deletes_idempotencytoken_before_case():
    """
    Static safety test:
    - IdempotencyToken import block exists (guarded optional import).
    - _maybe_delete(IdempotencyToken, ...) appears before _delete_all(Case, ...).
    This avoids FK violations or orphans when wiping Case.
    """
    script = Path("scripts/reset_storage_and_data_2.py").read_text(encoding="utf-8")

    # Import guard present for IdempotencyToken
    assert (
        re.search(r"from app\.models import IdempotencyToken", script)
        or "IdempotencyToken = None" in script
    ), "Missing IdempotencyToken optional import guard"

    # Ensure delete order: _maybe_delete(IdempotencyToken ... ) BEFORE _delete_all(Case ...)
    # Use non-greedy match across newlines to preserve order checking.
    order_ok = re.search(
        r"_maybe_delete\(\s*IdempotencyToken\b.*?_delete_all\(\s*Case\b",
        script,
        flags=re.DOTALL,
    )
    assert order_ok, "IdempotencyToken must be deleted before Case in reset script"
