param([int]$TopN = 50)

Write-Host "== codex_prep.ps1 :: IKTATAS2.0 =="
$repo = Resolve-Path "."
Set-Location $repo

# 1) Pinning hygiene (no installs, just checks)
$req = Test-Path ".\requirements.txt"
$con  = Test-Path ".\constraints.txt"
if(-not $req){ Write-Host "[WARN] requirements.txt missing" }
if(-not $con){ Write-Host "[WARN] constraints.txt missing" }

$build_heavy = @("lxml","cryptography","opencv-python","grpcio")
if($con){
  $pins = Get-Content .\constraints.txt
  $missing = $build_heavy | Where-Object { -not ($pins -match ("^" + [regex]::Escape($_) + "==")) }
  if($missing){ Write-Host "[NOTE] Consider wheel-friendly pins: $($missing -join ', ')" }
}

# 2) Locate heavy files for prompt exclusion
$heavy = Get-ChildItem -Recurse -File -Include *.py,*.html,*.css,*.js,*.sql,*.txt,*.md `
  | Sort-Object Length -Descending | Select-Object FullName,Length -First $TopN
$report = ($heavy | ForEach-Object { "{0}`t{1:N0}" -f $_.FullName,$_.Length }) -join "`n"
New-Item -ItemType Directory -Force -Path .\tools | Out-Null
Set-Content .\tools\.heavy_files.tsv $report -Encoding UTF8
Write-Host "[OK] Wrote tools\.heavy_files.tsv"

# 3) Generate/refresh CONTEXT_PACK.md (short + rules)
$pack = @(
"# CONTEXT_PACK — IKTATAS2.0",
"",
"## How to work fast",
"- Use FLASK.bat as usual (it may run pytest).",
"- Do NOT run pytest during Codex tasks.",
"- Run tools/FULLTEST.bat at the end, before commit.",
"",
"## Key entry points",
"- app/__init__.py (Flask app, binds, CSP, Jinja rules)",
"- app/views/auth.py (/szignal_cases)",
"- app/investigations/routes.py (separate DB bind)",
"- migrations/ (Alembic multi-bind, batch mode)",
"",
"## Hard rules",
"- Date-Safety Rule (no .date() in Jinja; precompute in Python).",
"- Investigations stay on separate DB bind.",
"- Alembic: batch mode, guarded column add, single-head.",
"",
"## Test shortcuts (for humans, not Codex)",
"- Full: pytest -q  (use tools/FULLTEST.bat)",
"",
"## Large files to avoid in prompts (see tools/.heavy_files.tsv)",
""
)
Set-Content .\CONTEXT_PACK.md ($pack -join "`n") -Encoding UTF8

Write-Host "== Done. No tests executed. Feed CONTEXT_PACK.md + small diffs to Codex =="
