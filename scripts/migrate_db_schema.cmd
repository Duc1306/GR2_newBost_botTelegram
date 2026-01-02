@echo off
echo ========================================
echo Database Schema Migration
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

echo.
echo ⚠️  WARNING: This will modify your database schema!
echo    - Create new indexes
echo    - Add new fields to existing documents
echo    - Create new collections
echo.
echo Press Ctrl+C to cancel, or
pause

python scripts\migrate_db_schema.py

echo.
echo ========================================
echo Migration Complete
echo ========================================
pause
