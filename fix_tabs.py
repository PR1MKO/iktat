from pathlib import Path

p = Path(".pre-commit-config.yaml")
s = p.read_text(encoding="utf-8")
fixed = s.replace("\t", "  ")  # replace tabs with 2 spaces
p.write_text(fixed, encoding="utf-8", newline="\n")
print(f"Fixed tabs → spaces in {p}")
