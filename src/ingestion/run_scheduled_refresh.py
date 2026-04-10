"""
Scheduled Refresh — chạy 1 lần rồi thoát.
==========================================
Dùng cho Render Cron Job (hoặc bất kỳ task scheduler nào):
  - Fetch tin mới từ tất cả kênh `active` trong DB
  - Xoá tin cũ hơn TELEGRAM_FETCH_DAYS ngày
  - Tạo lại AI summary nếu có tin mới

Lệnh chạy:
    python -m src.ingestion.run_scheduled_refresh

Render Cron schedule gợi ý: "0 1,13 * * *"
    → 1:00 UTC (8:00 sáng VN) và 13:00 UTC (8:00 tối VN)
"""
from __future__ import annotations
import asyncio
import sys
from loguru import logger

from src.db.mongo import get_db
from src.ingestion.channel_queue_worker import refresh_active_channels


async def main():
    db = get_db()
    logger.info("=== Scheduled refresh START ===")
    await refresh_active_channels(db)
    logger.info("=== Scheduled refresh DONE ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception(f"Scheduled refresh failed: {exc}")
        sys.exit(1)
