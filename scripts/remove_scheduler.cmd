@echo off
REM ============================================================
REM  Gỡ Auto-Startup của NewsBot (không cần Admin)
REM ============================================================
set LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\newsbot-fetch-daemon.lnk

if exist "%LNK%" (
    del /f "%LNK%"
    echo [OK] Da xoa startup shortcut: %LNK%
) else (
    echo [INFO] Khong tim thay startup shortcut.
)

REM Xoa task scheduler cu (neu co tu phien ban truoc)
schtasks /delete /tn "newsbot-fetch-morning" /f >nul 2>&1
schtasks /delete /tn "newsbot-fetch-evening" /f >nul 2>&1
schtasks /delete /tn "newsbot-fetch-auto" /f >nul 2>&1

echo [OK] Hoan tat. NewsBot se khong tu dong fetch khi khoi dong Windows nua.
pause
