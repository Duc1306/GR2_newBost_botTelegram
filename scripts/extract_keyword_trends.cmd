@echo off
echo ========================================
echo Extract Keyword Trends
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\extract_keyword_trends.py %*
pause
