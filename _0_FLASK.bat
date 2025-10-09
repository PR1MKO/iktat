@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =========================
REM CONFIG
REM =========================
set "PROJECT_DIR=C:\Users\kiss.istvan3\Desktop\folyamatok\IKTATAS2.0\forensic-case-tracker"
set "GIT_BRANCH=main"
set "FLASK_APP=app:create_app"
set "GIT_PAGER=more"

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo ================== IKTATAS2.0 — Safe Deploy Runner (NO-DB) ==================

REM 1) Stop Flask/Python
echo [1/10] Stopping any running Flask/Python...
tasklist | findstr /i "flask.exe python.exe" >nul
IF %ERRORLEVEL% EQU 0 (
    echo   Killing flask.exe and python.exe...
    taskkill /f /im flask.exe >nul 2>&1
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 2 >nul
) ELSE (
    echo   None found.
)

REM 2) Change to project folder
echo.
echo [2/10] Changing to project directory...
cd /d "%PROJECT_DIR%" || (echo   ERROR: Cannot cd to "%PROJECT_DIR%".& exit /b 1)

REM 3) Activate venv (prefer .venv, then venv; create venv if missing)
echo.
echo [3/10] Activating virtual environment...
IF EXIST ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) ELSE (
    echo   No venv found. Creating "venv"...
    python -m venv venv || (echo   ERROR: Failed to create venv.& exit /b 1)
    call "venv\Scripts\activate.bat"
)

REM 4) Ensure folders exist (non-DB)
echo.
echo [4/10] Ensuring required folders exist...
IF NOT EXIST "instance" mkdir "instance"
IF NOT EXIST "uploads"  mkdir "uploads"
REM Ensure project-specific upload roots
IF NOT EXIST "instance\uploads_cases"           mkdir "instance\uploads_cases"
IF NOT EXIST "instance\uploads_investigations"  mkdir "instance\uploads_investigations"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyyMMdd_HHmmss\""') do set "TS=%%i"
echo   Timestamp: %TS%

REM 5) Ensure dependencies (prod + dev) so pytest/pre-commit live in THIS venv
echo.
echo [5/10] Installing dependencies...
python -m pip install --upgrade pip || exit /b 1
pip install -r requirements.txt || exit /b 1
IF EXIST requirements-dev.txt (
    pip install -r requirements-dev.txt || exit /b 1
) ELSE (
    pip install pytest pytest-xdist coverage pre-commit ruff isort black iniconfig pluggy || exit /b 1
)
REM Quick sanity imports
python -c "import sys, sqlalchemy, pytest; print('Py:',sys.version.split()[0],' SA:',getattr(sqlalchemy,'__version__','?'),' PYTEST:',pytest.__version__)" || exit /b 1

REM 6) Run pre-commit (changed-only; one restage pass; fail-fast)
echo.
echo [6/10] Running pre-commit hooks (changed files)...
git add -A
pre-commit run --show-diff-on-failure || (
    echo   Hooks applied fixes; re-staging...
    git add -A
    pre-commit run --show-diff-on-failure || (echo   pre-commit still failing. & exit /b 1)
)
echo   pre-commit completed.

REM 7) Run tests (live output + tee to log); on failure, tail + summary and offer Notepad
echo.
echo [7/10] Running tests...
set "LOG_DIR=logs"
IF NOT EXIST "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\pytest_%TS%.log"
set "TAIL_LINES=200"

REM pick pytest exe explicitly (venv first)
set "PYTEST_EXE=pytest"
IF EXIST ".venv\Scripts\pytest.exe" set "PYTEST_EXE=.venv\Scripts\pytest.exe"
IF EXIST "venv\Scripts\pytest.exe"  set "PYTEST_EXE=venv\Scripts\pytest.exe"

REM write headers
> "%LOG_FILE%" echo ==== Python / Env ====
python -c "import sys,os;print(sys.version);print('VIRTUAL_ENV=',os.environ.get('VIRTUAL_ENV'))" >> "%LOG_FILE%" 2>&1
echo ==== Package pins (subset) ==== >> "%LOG_FILE%"
python -m pip freeze | findstr /R /C:"Flask" /C:"Jinja2" /C:"Werkzeug" /C:"SQLAlchemy" /C:"WTForms" /C:"ruff" /C:"black" /C:"isort" >> "%LOG_FILE%" 2>&1
echo ==== Running: %PYTEST_EXE% -q --maxfail=1 ==== >> "%LOG_FILE%"

REM Run pytest, stream to console, tee to log, preserve exit code
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$log=[IO.Path]::GetFullPath('%LOG_FILE%');" ^
  "& '%PYTEST_EXE%' '-q' '--maxfail=1' 2>&1 | Tee-Object -FilePath $log -Append;" ^
  "exit $LASTEXITCODE"
set "RC=%ERRORLEVEL%"

if NOT "%RC%"=="0" (
    echo.
    echo   ❌ Pytest FAILED. Full log: %LOG_FILE%
    echo.
    echo   ---- Last %TAIL_LINES% lines ----
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "Get-Content -Path '%LOG_FILE%' -Tail %TAIL_LINES% | ForEach-Object { $_ }"
    echo.
    echo   ---- Failure summary ----
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$p='^(=+ FAILURES =+|=+ ERRORS =+|E\s{2,}|^FAILED\s|^ERROR\s|^===.*(failed|errors).*)';" ^
      "Get-Content -Path '%LOG_FILE%' | Select-String -Pattern $p | ForEach-Object { $_.Line }"
    echo.
    set /p OPENLOG=Open full log in Notepad? [y/N]: 
    if /I "%OPENLOG%"=="Y" start "" notepad "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

echo   Tests passed. Log: %LOG_FILE%


REM 8) Commit
echo.
echo [8/10] Committing latest changes...
git add -A
git commit -m "Safe deploy (NO-DB): hooks->tests (%TS%)" || echo   Nothing to commit.

REM 9) Push (push the CURRENT branch; set upstream if missing)
echo.
echo [9/10] Pushing changes...
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set CURBR=%%b
for /f "tokens=*" %%u in ('git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2^>NUL') do set UP=%%u
echo   Current branch: %CURBR%
if "%UP%"=="" (
    echo   No upstream set; pushing and setting upstream to origin/%CURBR%...
    git push --set-upstream origin %CURBR% || exit /b 1
) else (
    echo   Upstream: %UP%
    git push || exit /b 1
)

REM 10) Start Flask
echo.
echo [10/10] Starting Flask...
set "FLASK_ENV=development"
python -m flask run

endlocal
exit /b 0