@echo off
REM Verify Telegram channels exist and are active
REM Kiểm tra các kênh Telegram có tồn tại và hoạt động

cd /d %~dp0\..
echo.
echo ========================================
echo Verify Telegram Channels
echo ========================================
echo.

python scripts\verify_channels.py %*

echo.
pause
