@echo off
REM ============================================================
REM  Setup Auto-Startup — Tự động fetch Telegram khi đăng nhập
REM ============================================================
REM  Script này KHÔNG cần quyền Administrator.
REM  Cách hoạt động:
REM    - Thêm fetch_daemon.cmd vào Windows Startup folder
REM    - Mỗi lần đăng nhập Windows, daemon tự khởi động
REM    - Daemon fetch Telegram mỗi INTERVAL_HOURS giờ liên tục
REM
REM  Gỡ cài:  scripts\remove_scheduler.cmd
REM ============================================================

setlocal
set ROOT=%~dp0\..

REM Khoảng thời gian (giờ) — mặc định 3 giờ
set INTERVAL_HOURS=3
if not "%1"=="" set INTERVAL_HOURS=%1

echo.
echo ============================================================
echo   Cài đặt Startup tự động cho NewsBot (không cần Admin)
echo   Fetch mỗi %INTERVAL_HOURS% giờ khi Windows khởi động
echo ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\register_task.ps1" %INTERVAL_HOURS%

echo.
pause

setlocal
set ROOT=%~dp0\..
set SCRIPT=%ROOT%\scripts\fetch_telegram.cmd

REM ── Tùy chỉnh khoảng thời gian (giờ) ──
set INTERVAL_HOURS=3
REM ────────────────────────────────────────

echo.
echo ============================================================
echo   Cài đặt Windows Task Scheduler cho NewsBot
echo   Fetch mỗi %INTERVAL_HOURS% giờ tự động
echo ============================================================

REM Xoá task cũ nếu tồn tại
schtasks /delete /tn "newsbot-fetch-morning" /f >nul 2>&1
schtasks /delete /tn "newsbot-fetch-evening" /f >nul 2>&1
schtasks /delete /tn "newsbot-fetch-auto" /f >nul 2>&1

REM Tạo task chạy mỗi 2 giờ (bắt đầu từ 00:00)
schtasks /create ^
  /tn "newsbot-fetch-auto" ^
  /tr "\"%SCRIPT%\"" ^
  /sc hourly ^
  /mo %INTERVAL_HOURS% ^
  /st 00:00 ^
  /ru "%USERNAME%" ^
  /f
if %errorlevel% neq 0 goto error

echo   [OK] Task: chạy mỗi %INTERVAL_HOURS% giờ (kể cả khi không mở VS Code)
echo.
echo ============================================================
echo   Hoàn tất! Tin tức Telegram sẽ fetch tự động mỗi %INTERVAL_HOURS% giờ.
echo.
echo   Kiểm tra: Task Scheduler ^> Task Scheduler Library
echo             ^> newsbot-fetch-auto
echo   Gỡ cài:  scripts\remove_scheduler.cmd
echo ============================================================
echo.
pause
exit /b 0

:error
echo.
echo [LỖI] Không thể tạo scheduled task. Kiểm tra lại quyền Administrator.
pause
exit /b 1
