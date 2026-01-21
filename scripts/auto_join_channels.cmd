@echo off
REM Auto join Telegram channels from channel.json
REM Tự động join các kênh Telegram từ file channel.json

cd /d %~dp0\..
echo.
echo ========================================
echo   AUTO JOIN TELEGRAM CHANNELS
echo ========================================
echo.
echo Dang doc kenh tu channel.json...
echo.

call venv\Scripts\activate.bat
python scripts\auto_join_channels.py %*

echo.
pause
