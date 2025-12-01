@echo off
echo ========================================
echo   Tao Session Telegram
echo ========================================
echo.
cd /d %~dp0\..
call venv\Scripts\activate.bat
python scripts\create_session.py
pause
