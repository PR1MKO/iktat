@echo off
setlocal enabledelayedexpansion

echo ═══ Activating virtual environment...

IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) ELSE (
    echo ❌ venv not found. Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

echo.
echo ═══ Checking git status...
git diff --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Local changes detected. Skipping git pull to avoid overwriting.
) ELSE (
    echo ═══ Pulling latest changes from GitHub...
    git pull origin main --rebase
)

echo.
echo ═══ Ensuring required folders exist...
IF NOT EXIST instance mkdir instance
IF NOT EXIST uploads mkdir uploads

echo.
echo ═══ Upgrading database...
flask db upgrade

echo.
echo ═══ Starting Flask...
flask run

endlocal
