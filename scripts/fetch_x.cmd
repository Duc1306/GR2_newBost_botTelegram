@echo off
REM ============================================
REM  X (Twitter) Worker Helper — via Apify
REM ============================================
REM  Usage:
REM    fetch_x.cmd              - Cào cả keyword + user (mode=both)
REM    fetch_x.cmd user         - Chỉ cào từ tài khoản DB/env (Actor B)
REM    fetch_x.cmd keyword      - Chỉ cào theo từ khoá (Actor A)
REM    fetch_x.cmd user 100     - Cào tài khoản, tối đa 100 tweet/user
REM    fetch_x.cmd keyword 50   - Cào keyword, tối đa 50 tweet/keyword
REM ============================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

REM Parse arguments
set MODE=both
set MAX=50

if "%1"=="user"    set MODE=user
if "%1"=="keyword" set MODE=keyword

REM Tham số thứ 2 là số lượng tối đa (tuỳ chọn)
if not "%2"=="" set MAX=%2

echo.
echo ============================================
echo   X (Twitter) Worker — Apify
echo   Mode : %MODE%
echo   Max  : %MAX% tweets/item
echo   APIFY token must be set in .env
echo ============================================
echo.

python -m src.ingestion.x_worker --mode %MODE% --max %MAX%

echo.
echo ============================================
echo   X Worker finished.
echo ============================================
echo.

pause
