@echo off
setlocal enabledelayedexpansion

REM === Close any running Flask processes ===
echo ═══ Stopping any running Flask servers...
tasklist | findstr /i "flask.exe python.exe" >nul
IF %ERRORLEVEL% EQU 0 (
    echo ⚠️ Flask or Python is running. Attempting to kill...
    taskkill /f /im flask.exe >nul 2>&1
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 1 >nul
) ELSE (
    echo ✅ No running Flask/Python processes found.
)

REM === Change to project directory ===
cd /d "C:\Users\kiss.istvan3\Desktop\folyamatok\IKTATAS2.0\forensic-case-tracker"

REM === Activate venv ===
echo ═══ Activating virtual environment...
IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) ELSE (
    echo ❌ venv not found. Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
)

REM === Git add, commit, push ===
echo.
echo ═══ Committing and pushing latest changes...
git add .
git commit -m "✅ Apply Codex update: toxi"
IF %ERRORLEVEL% NEQ 0 (
    echo ⚠️ No new changes to commit.
)
git push origin main
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Git push failed. Aborting launch.
    pause
    exit /b
)

REM === Pull just in case ===
echo.
echo ═══ Pulling latest changes (safety sync)...
git pull origin main --rebase

REM === Ensure folders exist ===
echo.
echo ═══ Ensuring required folders exist...
IF NOT EXIST instance mkdir instance
IF NOT EXIST uploads mkdir uploads

REM === DB upgrade ===
echo.
echo ═══ Upgrading database...
flask db upgrade

REM === Start Flask ===
echo.
echo ═══ Starting Flask...
flask run

endlocal
