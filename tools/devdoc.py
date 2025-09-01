from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def _resolve_path(path: str | None) -> Path:
    if path:
        return Path(path)
    env_path = os.environ.get("DEV_DOC_PATH")
    if env_path:
        return Path(env_path)
    return Path("docs/DEV_DOC.md")


def _compose_block(heads: str, risks: str, next_steps: str) -> str:
    utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    bud = datetime.now(ZoneInfo("Europe/Budapest")).replace(microsecond=0).isoformat()
    return (
        f"### {utc} / {bud}\n"
        f"**Heads:** {heads.strip()}\n"
        f"**Risks:** {risks.strip()}\n"
        f"**Next:** {next_steps.strip()}\n"
        f"---\n"
    )


def _atomic_append(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    counter = 0
    temp = target.with_suffix(target.suffix + f".tmp{counter}")
    while temp.exists():
        counter += 1
        temp = target.with_suffix(target.suffix + f".tmp{counter}")
    data = b""
    if target.exists():
        with target.open("rb") as f:
            data = f.read()
    with temp.open("wb") as f:
        f.write(data)
        f.write(text.encode("utf-8"))
    os.replace(temp, target)


def append_entry(
    heads: str, risks: str, next_steps: str, path: str | None = None
) -> Path:
    target = _resolve_path(path)
    block = _compose_block(heads, risks, next_steps)
    _atomic_append(target, block)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append an entry to the Dev Doc")
    parser.add_argument("--heads", required=True)
    parser.add_argument("--risks", required=True)
    parser.add_argument("--next", dest="next_steps", required=True)
    parser.add_argument("--path")
    args = parser.parse_args(argv)
    try:
        append_entry(args.heads, args.risks, args.next_steps, args.path)
    except Exception as exc:  # pragma: no cover - simple CLI failure path
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
