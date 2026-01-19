@echo off
REM Script to fix misclassified topics in database
echo ========================================
echo Fix Misclassified Topics
echo ========================================
echo.

REM Dry run first (preview changes)
echo [1/2] Running DRY RUN to preview changes...
python scripts\fix_misclassified_topics.py
echo.

REM Ask user to confirm
echo.
set /p confirm="Do you want to apply these changes? (y/n): "
if /i "%confirm%"=="y" (
    echo.
    echo [2/2] Applying changes to database...
    python scripts\fix_misclassified_topics.py --apply
    echo.
    echo Done!
) else (
    echo.
    echo Operation cancelled.
)

pause
