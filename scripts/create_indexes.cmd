@echo off
echo ========================================
echo   Tao indexes MongoDB
echo ========================================
echo.
cd /d %~dp0\..
call venv\Scripts\activate.bat
python scripts\create_indexes.py
pause
