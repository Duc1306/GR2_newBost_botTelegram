@echo off
REM ============================================
REM  SCRIPT CHÍNH - LẤY TIN MỚI TỪ TELEGRAM
REM ============================================
REM  Chức năng:
REM  - Lấy 100 tin mới nhất từ mỗi channel
REM  - Chỉ lấy tin có link bên ngoài
REM  - Scrape full article (bỏ qua vnexpress)
REM  - Phân loại chủ đề tự động
REM  - Thời gian: ~5-10 phút
REM ============================================

setlocal ENABLEDELAYEDEXPANSION
set ROOT=%~dp0\..
cd /d %ROOT%
set PYTHONPATH=%ROOT%

call venv\Scripts\activate.bat

echo.
echo ========================================================
echo   FETCHING LATEST TELEGRAM POSTS
echo   - 100 posts per channel
echo   - Links only + Article scraping
echo   - Time: ~5-10 minutes
echo ========================================================
echo.

python -m src.ingestion.telegram_worker --scrape --links-only

echo.
echo ========================================
echo   DONE! Check MongoDB for new posts
echo ========================================
echo.

endlocal
pause
