# scripts/wipe_cases.py
# Deprecated entrypoint: intentionally disabled to avoid accidental data loss.
import sys


def main() -> int:
    print(
        "This command is disabled. Use scripts/reset_storage_and_data_2.py with --force "
        "--i-know-what-im-doing and set ALLOW_INSTANCE_DELETION=1.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
