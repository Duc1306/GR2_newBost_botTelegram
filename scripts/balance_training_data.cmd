@echo off
REM Balance training data to fix class imbalance
REM Cân bằng dữ liệu training để sửa lỗi mất cân bằng

cd /d %~dp0\..
echo.
echo ========================================
echo Balance Training Data
echo ========================================
echo.

python scripts\balance_training_data.py %*

echo.
pause
