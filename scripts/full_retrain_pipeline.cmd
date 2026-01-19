@echo off
REM Full pipeline to retrain ML model with improved classifier
echo ========================================
echo Full ML Model Retraining Pipeline
echo ========================================
echo.
echo This will:
echo   [1] Reclassify all posts with improved rules
echo   [2] Balance dataset
echo   [3] Train new ML model
echo.
echo ========================================
echo.

REM Run dry-run first
echo Step 1: Dry run to preview changes...
echo.
python scripts\full_retrain_pipeline.py
echo.

REM Ask for confirmation
set /p confirm="Do you want to apply changes and retrain model? (y/n): "
if /i "%confirm%"=="y" (
    echo.
    echo Starting full pipeline with --apply flag...
    python scripts\full_retrain_pipeline.py --apply --balanced --target-samples 500 --limit 10000
    echo.
    echo ========================================
    echo Pipeline completed!
    echo ========================================
) else (
    echo.
    echo Operation cancelled.
)

pause
