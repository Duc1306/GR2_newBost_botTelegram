@echo off
REM ============================================
REM  Telegram Worker Helper
REM ============================================
REM  Usage:
REM    fetch_telegram.cmd           - Quick fetch (200 posts/channel)
REM    fetch_telegram.cmd full      - Full fetch (1000 posts/channel)
REM    fetch_telegram.cmd scrape    - Quick + scrape articles
REM    fetch_telegram.cmd full scrape - Full + scrape articles
REM ============================================

setlocal
set ROOT=%~dp0\..
cd /d %ROOT%

REM Activate venv
call venv\Scripts\activate.bat

REM Parse arguments
set MODE=quick
set SCRAPE=

if "%1"=="full" set MODE=full
if "%2"=="scrape" set SCRAPE=--scrape
if "%1"=="scrape" set SCRAPE=--scrape

REM Run telegram worker
echo.
echo ============================================
if "%MODE%"=="full" (
    echo   Full Fetch Mode ^(1000 posts/channel^)
    echo   Estimated time: 10-30 minutes
    python -m src.ingestion.telegram_worker --full %SCRAPE%
) else (
    echo   Quick Fetch Mode ^(200 posts/channel^)
    echo   Estimated time: 3-5 minutes
    python -m src.ingestion.telegram_worker %SCRAPE%
)
echo ============================================
echo.

pause
