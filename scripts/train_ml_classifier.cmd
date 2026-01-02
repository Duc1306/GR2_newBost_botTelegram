@echo off
echo ========================================
echo Training ML Topic Classifier
echo ========================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

python scripts\train_ml_classifier.py %*
pause
