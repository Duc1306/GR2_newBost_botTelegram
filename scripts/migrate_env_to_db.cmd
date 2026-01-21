@echo off
REM Migrate channels from .env to database
REM Chuyen cac kenh tu .env vao database

cd /d %~dp0\..
echo.
echo ========================================
echo   MIGRATE KENH TU .ENV VAO DATABASE
echo ========================================
echo.

call venv\Scripts\activate.bat
python scripts\migrate_env_to_db.py

echo.
pause
