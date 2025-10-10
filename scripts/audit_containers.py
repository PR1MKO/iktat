#!/usr/bin/env python3
"""Audit Bootstrap container usage in Jinja templates."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

TAG_RE = re.compile(
    r"(?P<open><div\b[^>]*?>)|(?P<close></div\s*>)", re.IGNORECASE | re.DOTALL
)
CLASS_RE = re.compile(
    r'class\s*=\s*(["\'])(?P<value>.*?)(\1)', re.IGNORECASE | re.DOTALL
)
BLOCK_RE = re.compile(r"{%\s*block\s+content\s*%}", re.IGNORECASE)
ENDBLOCK_RE = re.compile(r"{%\s*endblock(?:\s+content)?\s*%}", re.IGNORECASE)
EXTENDS_RE = re.compile(
    r'{%\s*extends\s+["\'](?P<name>[^"\']+)["\']\s*%}', re.IGNORECASE
)
INCLUDE_RE = re.compile(
    r'{%\s*include\s+["\'](?P<name>[^"\']+)["\']\s*%}', re.IGNORECASE
)
IMPORT_RE = re.compile(
    r'{%\s*(?:import|from)\s+["\'](?P<name>[^"\']+)["\']', re.IGNORECASE
)

TARGET_CLASS_PREFIXES = {
    "container": {"container", "container-fluid"},
    "row": {"row"},
    "col": {"col", "col-auto"},
}


@dataclass
class StackEntry:
    tag: str
    line: int
    classes: List[str]
    target: Optional[str]


class TemplateAnalyzer:
    def __init__(self, template_root: Path) -> None:
        self.template_root = template_root
        self.project_root = Path(__file__).resolve().parents[1]
        self.files = sorted(self.template_root.rglob("*.html"))
        self.base_wrapper = self._detect_base_wrapper()

    def _relpath(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.project_root))
        except ValueError:
            try:
                return str(path.resolve().relative_to(self.template_root))
            except ValueError:
                return str(path)

    def _iter_div_tokens(
        self, text: str, *, limit: Optional[int] = None
    ) -> Iterator[re.Match[str]]:
        for match in TAG_RE.finditer(text):
            if limit is not None and match.start() >= limit:
                break
            yield match

    def _parse_classes(self, raw_tag: str) -> List[str]:
        match = CLASS_RE.search(raw_tag)
        if not match:
            return []
        value = match.group("value")
        # Remove Jinja expressions that may appear inside class attribute
        clean = re.sub(r"{%.*?%}|{{.*?}}", " ", value)
        classes = [cls.strip() for cls in clean.split() if cls.strip()]
        return classes

    def _detect_target(self, classes: Iterable[str]) -> Optional[str]:
        for cls in classes:
            lowered = cls.lower()
            if any(lowered == opt for opt in TARGET_CLASS_PREFIXES["container"]):
                return "container"
        for cls in classes:
            lowered = cls.lower()
            if lowered == "row" or lowered.startswith("row-"):
                return "row"
        for cls in classes:
            lowered = cls.lower()
            if lowered == "col" or lowered.startswith("col-"):
                return "col"
        return None

    def _detect_base_wrapper(self) -> Optional[str]:
        base = self.template_root / "base.html"
        if not base.exists():
            return None
        text = base.read_text(encoding="utf-8")
        block_match = BLOCK_RE.search(text)
        if not block_match:
            return None
        stack: List[StackEntry] = []
        for match in self._iter_div_tokens(text, limit=block_match.start()):
            if match.group("open"):
                raw = match.group("open")
                is_self_closing = raw.rstrip().endswith("/>")
                classes = self._parse_classes(raw)
                target = self._detect_target(classes)
                entry = StackEntry(
                    "div", text.count("\n", 0, match.start()) + 1, classes, target
                )
                if not is_self_closing:
                    stack.append(entry)
            else:
                if stack:
                    stack.pop()
        for entry in reversed(stack):
            if entry.target == "container":
                return "container"
        return None

    def audit(self) -> dict:
        issues: List[dict] = []
        counts: Counter[str] = Counter()
        stats: Counter[str] = Counter()
        for path in self.files:
            text = path.read_text(encoding="utf-8")
            file_issues, file_stats = self._audit_file(path, text)
            for issue in file_issues:
                issues.append(issue)
                counts[issue["type"]] += 1
            for key, value in file_stats.items():
                stats[key] += value
        report = {
            "root": str(self._relpath(self.template_root)),
            "issues": sorted(
                issues,
                key=lambda item: (item["type"], item["file"], item.get("line", 0)),
            ),
            "summary": {
                "total_files": len(self.files),
                "issues_by_type": dict(counts),
                "totals": dict(stats),
                "base_wrapper": self.base_wrapper,
            },
        }
        return report

    def _audit_file(self, path: Path, text: str) -> tuple[List[dict], Counter[str]]:
        rel = self._relpath(path)
        stack: List[StackEntry] = []
        issues: List[dict] = []
        stats: Counter[str] = Counter()
        partial_container_reported = False
        tokens = list(TAG_RE.finditer(text))
        for match in tokens:
            line = text.count("\n", 0, match.start()) + 1
            if match.group("open"):
                raw = match.group("open")
                is_self_closing = raw.rstrip().endswith("/>")
                classes = self._parse_classes(raw)
                target = self._detect_target(classes)
                entry = StackEntry("div", line, classes, target)
                if target:
                    stats[f"open_{target}"] += 1
                if target == "container" and not partial_container_reported:
                    if any(
                        part in {"includes", "macros"} for part in path.parts
                    ) or path.name.startswith("_"):
                        issues.append(
                            {
                                "file": rel,
                                "line": line,
                                "type": "container_in_partial",
                                "message": "Containers must be controlled by page templates; remove wrapper from include/macro.",
                            }
                        )
                        partial_container_reported = True
                if not is_self_closing:
                    stack.append(entry)
            else:
                if not stack:
                    issues.append(
                        {
                            "file": rel,
                            "line": line,
                            "type": "overclosed_div",
                            "message": "Encountered closing </div> without matching opening tag.",
                        }
                    )
                else:
                    stack.pop()
        for entry in stack:
            if entry.target:
                issues.append(
                    {
                        "file": rel,
                        "line": entry.line,
                        "type": f"unclosed_{entry.target}",
                        "message": f"<{entry.tag}> with class {' '.join(entry.classes)} not closed.",
                    }
                )
        if self.base_wrapper == "container":
            # Detect double container around content block
            if EXTENDS_RE.search(text):
                block_match = BLOCK_RE.search(text)
                end_match = (
                    ENDBLOCK_RE.search(text, block_match.end()) if block_match else None
                )
                if block_match and end_match:
                    inner = text[block_match.end() : end_match.start()]
                    first_tag = re.search(
                        r"<div\b[^>]*?>", inner, re.IGNORECASE | re.DOTALL
                    )
                    if first_tag:
                        classes = self._parse_classes(first_tag.group(0))
                        target = self._detect_target(classes)
                        if target == "container":
                            issues.append(
                                {
                                    "file": rel,
                                    "line": block_match.start(),
                                    "type": "double_container",
                                    "message": "Base template already wraps content; remove extra container in child template.",
                                }
                            )
        return issues, stats

    def build_graph(self, templates: Iterable[str]) -> List[dict]:
        graphs: List[dict] = []
        for name in templates:
            template_path = self._resolve_template_name(name)
            if not template_path or not template_path.exists():
                graphs.append(
                    {
                        "template": name,
                        "error": "not_found",
                    }
                )
                continue
            text = template_path.read_text(encoding="utf-8")
            rel = self._relpath(template_path)
            entries = []
            for regex, label in (
                (EXTENDS_RE, "extends"),
                (INCLUDE_RE, "includes"),
                (IMPORT_RE, "imports"),
            ):
                matches = []
                for match in regex.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    matches.append({"template": match.group("name"), "line": line})
                entries.append((label, matches))
            graphs.append(
                {
                    "template": rel,
                    **{label: matches for label, matches in entries},
                }
            )
        return graphs

    def _resolve_template_name(self, name: str) -> Optional[Path]:
        candidate = Path(name)
        if candidate.is_absolute():
            return candidate
        relative = self.template_root / candidate
        if relative.exists():
            return relative
        # try ensure .html suffix
        if relative.suffix != ".html":
            relative = relative.with_suffix(".html")
            if relative.exists():
                return relative
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Bootstrap containers in Jinja templates."
    )
    parser.add_argument(
        "--root", default="app/templates", help="Template root directory"
    )
    parser.add_argument(
        "--graph",
        nargs="*",
        help="Template names (relative to root) to include in the template graph output.",
    )
    parser.add_argument(
        "--indent", type=int, default=2, help="JSON indentation (default: 2)"
    )
    args = parser.parse_args(argv)

    template_root = Path(args.root)
    if not template_root.exists():
        parser.error(f"Template root '{template_root}' does not exist")

    analyzer = TemplateAnalyzer(template_root)
    report = analyzer.audit()
    if args.graph:
        report["graphs"] = analyzer.build_graph(args.graph)
    json.dump(report, sys.stdout, indent=args.indent, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if not report["issues"] else 1


if __name__ == "__main__":
    sys.exit(main())
