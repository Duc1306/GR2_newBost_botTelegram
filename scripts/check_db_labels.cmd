@echo off
echo ========================================
echo Checking Database Labels
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\check_db_labels.py
pause
