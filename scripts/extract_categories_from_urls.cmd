@echo off
REM Extract categories from news URLs
echo ========================================
echo Extract Categories from News URLs
echo ========================================
echo.
echo This will extract categories/topics from news URLs
echo and use them as ground truth for training.
echo.

REM Dry run first
echo [1/2] Running DRY RUN to preview...
python scripts\extract_categories_from_urls.py --limit 100
echo.

set /p confirm="Continue with full extraction? (y/n): "
if /i "%confirm%"=="y" (
    echo.
    echo [2/2] Extracting categories from URLs...
    python scripts\extract_categories_from_urls.py --apply --limit 1000 --delay 0.3
    echo.
    echo Done!
) else (
    echo.
    echo Cancelled.
)

pause
