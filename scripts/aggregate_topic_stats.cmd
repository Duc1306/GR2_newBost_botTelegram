@echo off
echo ========================================
echo Aggregate Topic Statistics
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\aggregate_topic_stats.py %*
pause
