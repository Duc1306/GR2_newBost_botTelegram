@echo off
REM ============================================================
REM  Fetch Daemon — tự động fetch Telegram mỗi N giờ
REM ============================================================
REM  Chạy lệnh này 1 lần, nó sẽ:
REM    1. Fetch ngay lập tức khi khởi động
REM    2. Lặp lại mỗi INTERVAL_HOURS giờ tự động
REM
REM  Cách dùng:
REM    fetch_daemon.cmd           - Fetch mỗi 2 giờ (mặc định)
REM    fetch_daemon.cmd 1         - Fetch mỗi 1 giờ
REM    fetch_daemon.cmd 4         - Fetch mỗi 4 giờ
REM
REM  Tắt daemon: Đóng cửa sổ này hoặc nhấn Ctrl+C
REM ============================================================

setlocal ENABLEDELAYEDEXPANSION
set ROOT=%~dp0\..
cd /d %ROOT%

REM Khoảng thời gian (giờ) — mặc định 2 giờ
set INTERVAL_HOURS=2
if not "%1"=="" set INTERVAL_HOURS=%1

REM Tính giây cho timeout
set /a INTERVAL_SEC=%INTERVAL_HOURS% * 3600

REM Kích hoạt venv
call venv\Scripts\activate.bat

echo.
echo ============================================================
echo   NewsBot Fetch Daemon - Đang chạy tự động
echo   Fetch mỗi %INTERVAL_HOURS% giờ (%INTERVAL_SEC% giây)
echo   Nhấn Ctrl+C để dừng
echo ============================================================
echo.

:loop
echo [%DATE% %TIME%] Bắt đầu fetch Telegram...
python -m src.ingestion.run_scheduled_refresh
echo [%DATE% %TIME%] Fetch xong. Chờ %INTERVAL_HOURS% giờ...
echo.

REM Đếm ngược (hiện thị tiến trình chờ mỗi 5 phút)
set /a REMAINING=%INTERVAL_SEC%
:wait_loop
if %REMAINING% LEQ 0 goto loop

REM Hiện thị thông báo mỗi 300 giây (5 phút)
set /a WAIT_CHUNK=300
if %REMAINING% LSS %WAIT_CHUNK% set WAIT_CHUNK=%REMAINING%
set /a REMAINING_MIN=%REMAINING% / 60
echo    [%TIME%] Còn khoảng %REMAINING_MIN% phút nữa sẽ fetch lại...
timeout /t %WAIT_CHUNK% /nobreak >nul

set /a REMAINING=%REMAINING% - %WAIT_CHUNK%
goto wait_loop
