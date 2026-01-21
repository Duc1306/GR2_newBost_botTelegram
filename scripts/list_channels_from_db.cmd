@echo off
REM List all Telegram channels from database
REM Xem danh sách các kênh Telegram từ database

cd /d %~dp0\..
echo.
echo ========================================
echo   DANH SACH KENH TU DATABASE
echo ========================================
echo.

call venv\Scripts\activate.bat
python scripts\list_channels_from_db.py

echo.
pause
