@echo off
REM ============================================
REM  LẤY DỮ LIỆU CŨ - ĐẦY ĐỦ (CÓ SCRAPE)
REM ============================================
REM  Chức năng:
REM  - Lấy 1000 tin cũ từ mỗi channel
REM  - Chỉ lấy tin có link bên ngoài
REM  - Scrape full article (chậm, bỏ qua vnexpress)
REM  - Phân loại chủ đề tự động
REM  - Thời gian: ~1-2 giờ
REM ============================================
REM  LƯU Ý: vnexpress.net bị block scraping (HTTP 406)
REM  -> Chỉ lưu link, không lấy full content từ vnexpress
REM ============================================

setlocal ENABLEDELAYEDEXPANSION
set ROOT=%~dp0\..
cd /d %ROOT%
set PYTHONPATH=%ROOT%

call venv\Scripts\activate.bat

echo.
echo ========================================================
echo   FETCHING HISTORICAL DATA - FULL SCRAPING MODE
echo   - 1000 posts per channel (historical)
echo   - Links only + Full article scraping
echo   - vnexpress.net: Link only (no scraping)
echo   - Time: ~1-2 hours
echo ========================================================
echo.

python -m src.ingestion.telegram_worker --full --scrape --links-only

echo.
echo ========================================
echo   DONE! Check MongoDB for full articles
echo ========================================
echo.

endlocal
pause
