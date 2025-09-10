# Usage: powershell -ExecutionPolicy Bypass -File tools/bootstrap_constraints.ps1
Write-Host "== bootstrap_constraints.ps1 =="
if (Test-Path venv\Scripts\activate.ps1) { . venv\Scripts\activate.ps1 }
Write-Host "[*] Freezing current env to constraints.txt ..."
python -m pip freeze --all | Sort-Object -Unique | Out-File -Encoding ASCII constraints.txt
Write-Host "[OK] constraints.txt written. Install with:"
Write-Host "    pip install -r requirements.txt -c constraints.txt"
