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
git status --porcelain | findstr . >nul
IF %ERRORLEVEL%==0 (
    echo ⚠️  Uncommitted changes detected. Skipping git pull.
) ELSE (
    echo ═══ Pulling latest changes...
    git pull
)

echo.
echo ═══ Ensuring required folders exist...
IF NOT EXIST "instance" mkdir instance
IF NOT EXIST "uploads" mkdir uploads

echo.
echo ═══ Upgrading database...
flask db upgrade || (
    echo ❌ Flask DB upgrade failed. Aborting.
    exit /b 1
)

echo.
echo ═══ Starting Flask...
flask run

endlocal
