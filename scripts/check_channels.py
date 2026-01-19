"""Script kiểm tra tên kênh Telegram có tồn tại không.
Dùng để verify các kênh trong TELEGRAM_CHANNELS trước khi chạy ingestion.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telethon import TelegramClient
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING
from src.ingestion.sources import CHANNELS

async def check_channels():
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print(" Thiếu TELEGRAM_API_ID hoặc TELEGRAM_API_HASH trong .env")
        return
    
    if TELEGRAM_SESSION_STRING:
        client = TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    else:
        print(" Thiếu TELEGRAM_SESSION_STRING. Chạy create_session.py trước.")
        return
    
    print(f" Kiểm tra {len(CHANNELS)} kênh...\n")
    
    async with client:
        valid_channels = []
        invalid_channels = []
        
        for ch in CHANNELS:
            try:
                entity = await client.get_entity(ch)
                title = getattr(entity, 'title', ch)
                valid_channels.append((ch, title))
                print(f" {ch} → {title}")
            except Exception as e:
                invalid_channels.append((ch, str(e)))
                print(f" {ch} → {e}")
        
        print(f"\ Tổng kết:")
        print(f"    Hợp lệ: {len(valid_channels)}/{len(CHANNELS)}")
        print(f"    Không tìm thấy: {len(invalid_channels)}/{len(CHANNELS)}")
        
        if invalid_channels:
            print(f"\ Gợi ý sửa các kênh không hợp lệ:")
            print(f"   1. Mở Telegram → tìm kiếm kênh")
            print(f"   2. Vào kênh → xem username (@ ở trên cùng)")
            print(f"   3. Cập nhật tên kênh đúng vào .env")

if __name__ == "__main__":
    asyncio.run(check_channels())
