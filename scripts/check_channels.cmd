@echo off
echo ========================================
echo   Kiem tra ten kenh Telegram
echo ========================================
echo.
cd /d %~dp0\..
call venv\Scripts\activate.bat
python scripts\check_channels.py
pause
