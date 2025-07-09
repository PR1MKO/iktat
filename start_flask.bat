@echo off
chcp 65001 >nul

echo ═══ Cleaning workspace (except this file)...
git reset --hard
git clean -xdf -e start_flask.bat

echo ═══ Pulling latest changes...
git pull origin main

echo ═══ Activating virtual environment...
call venv\Scripts\activate.bat

echo ═══ Upgrading database...
flask db upgrade

echo ═══ Starting Flask...
python run.py
