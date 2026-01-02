@echo off
echo ========================================
echo Auto Retrain ML Model
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\auto_retrain.py %*
pause
