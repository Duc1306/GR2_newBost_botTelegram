@echo off
REM Train ML classifier with class_weight='balanced' (RECOMMENDED)
REM Giữ toàn bộ dữ liệu, SVM tự động cân bằng

cd /d %~dp0\..
echo.
echo ========================================
echo Train ML Classifier (Class Weight Balanced)
echo ========================================
echo.

python scripts\train_with_class_weight.py %*

echo.
pause
