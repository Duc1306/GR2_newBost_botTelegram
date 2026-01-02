@echo off
echo ========================================
echo Predicting Topics for Unlabeled Posts
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\predict_topics.py %*
pause
