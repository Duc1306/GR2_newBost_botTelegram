"""
Script tự động join các kênh Telegram từ channel.json
Tự động join các kênh và lưu metadata vào database
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    UsernameInvalidError,
    UsernameNotOccupiedError,
    ChannelPrivateError,
    FloodWaitError,
    UserAlreadyParticipantError,
    ChatWriteForbiddenError
)
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING
from src.processing.category_mapper import map_category_to_topic
from src.db.mongo import get_db
from datetime import datetime, timezone
import time


async def load_channels_from_json(json_path: str = "channel.json") -> list[dict]:
    """Đọc danh sách kênh từ channel.json"""
    json_file = Path(json_path)
    
    if not json_file.exists():
        print(f"❌ Không tìm thấy file: {json_path}")
        return []
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            channels = json.load(f)
        
        # Chỉ lấy các channel Telegram
        telegram_channels = [ch for ch in channels if ch.get('platform') == 'telegram']
        print(f"📋 Đọc được {len(telegram_channels)} kênh Telegram từ {json_path}")
        return telegram_channels
    
    except Exception as e:
        print(f"❌ Lỗi đọc file {json_path}: {e}")
        return []


async def join_channel(client: TelegramClient, channel_info: dict) -> tuple[bool, str, dict]:
    """
    Join một kênh Telegram
    
    Returns:
        (success: bool, message: str, metadata: dict)
    """
    username = channel_info.get('username', '').strip().lstrip('@')
    category_en = channel_info.get('category', 'Other')
    
    # Map category sang topic tiếng Việt
    topic_vi = map_category_to_topic(category_en)
    
    metadata = {
        'username': username,
        'category_original': category_en,
        'topic_vietnamese': topic_vi,
        'link': channel_info.get('link', ''),
        'platform': 'telegram',
    }
    
    if not username:
        return False, "Tên kênh trống", metadata
    
    try:
        # Lấy thông tin entity
        entity = await client.get_entity(username)
        title = getattr(entity, 'title', username)
        participants_count = getattr(entity, 'participants_count', None)
        
        metadata['title'] = title
        metadata['participants_count'] = participants_count
        metadata['entity_id'] = entity.id
        
        # Thử join kênh
        try:
            await client(JoinChannelRequest(entity))
            return True, f"✅ Joined: {title} ({topic_vi})", metadata
        except UserAlreadyParticipantError:
            return True, f"✓ Đã join trước: {title} ({topic_vi})", metadata
        except ChatWriteForbiddenError:
            # Kênh public không cho join (chỉ xem) - vẫn coi là thành công
            return True, f"ℹ️ Kênh công khai (chỉ đọc): {title} ({topic_vi})", metadata
            
    except UsernameInvalidError:
        return False, f"❌ Tên kênh không hợp lệ: @{username}", metadata
    except UsernameNotOccupiedError:
        return False, f"❌ Kênh không tồn tại: @{username}", metadata
    except ChannelPrivateError:
        return False, f"🔒 Kênh riêng tư: @{username}", metadata
    except FloodWaitError as e:
        wait_time = e.seconds
        return False, f"⏳ Rate limit - chờ {wait_time}s: @{username}", metadata
    except Exception as e:
        return False, f"❌ Lỗi: @{username} - {str(e)}", metadata


def save_channel_metadata(db, metadata: dict):
    """Lưu metadata kênh vào database (collection: channel_metadata)"""
    try:
        collection = db['channel_metadata']
        
        # Upsert: cập nhật nếu đã tồn tại, insert nếu chưa
        collection.update_one(
            {'username': metadata['username']},
            {
                '$set': {
                    **metadata,
                    'updated_at': datetime.now(timezone.utc)
                },
                '$setOnInsert': {
                    'created_at': datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ Lỗi lưu metadata cho {metadata.get('username')}: {e}")


async def auto_join_channels(channel_json_path: str = "channel.json", delay: float = 2.0):
    """
    Tự động join các kênh từ channel.json
    
    Args:
        channel_json_path: Đường dẫn tới file channel.json
        delay: Thời gian chờ giữa các lần join (giây) để tránh rate limit
    """
    # Kiểm tra config
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Thiếu TELEGRAM_API_ID hoặc TELEGRAM_API_HASH trong .env")
        return
    
    if not TELEGRAM_SESSION_STRING:
        print("❌ Thiếu TELEGRAM_SESSION_STRING. Chạy scripts/create_session.py trước.")
        return
    
    # Load channels từ JSON
    channels = await load_channels_from_json(channel_json_path)
    if not channels:
        return
    
    # Kết nối Telegram
    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        int(TELEGRAM_API_ID),
        TELEGRAM_API_HASH
    )
    
    # Kết nối database
    db = get_db()
    
    print("\n" + "="*80)
    print("🤖 BẮT ĐẦU AUTO JOIN TELEGRAM CHANNELS")
    print("="*80)
    
    async with client:
        if not await client.is_user_authorized():
            print("❌ Session không hợp lệ. Chạy scripts/create_session.py để tạo session mới.")
            return
        
        me = await client.get_me()
        print(f"✓ Đăng nhập thành công: {me.first_name} (@{me.username})")
        print(f"✓ Bắt đầu join {len(channels)} kênh...\n")
        
        success_count = 0
        already_joined = 0
        failed_count = 0
        
        for i, channel_info in enumerate(channels, 1):
            username = channel_info.get('username', '').strip().lstrip('@')
            print(f"\n[{i}/{len(channels)}] Xử lý: @{username}")
            
            # Join channel
            success, message, metadata = await join_channel(client, channel_info)
            print(f"  {message}")
            
            # Lưu metadata vào database
            if success:
                save_channel_metadata(db, metadata)
                if "Đã join trước" in message or "chỉ đọc" in message:
                    already_joined += 1
                else:
                    success_count += 1
            else:
                failed_count += 1
            
            # Chờ để tránh rate limit
            if i < len(channels):
                await asyncio.sleep(delay)
    
    # Tổng kết
    print("\n" + "="*80)
    print("📊 KẾT QUẢ")
    print("="*80)
    print(f"✅ Join mới thành công: {success_count}/{len(channels)}")
    print(f"✓  Đã join trước đó:    {already_joined}/{len(channels)}")
    print(f"❌ Thất bại:            {failed_count}/{len(channels)}")
    print(f"📝 Tổng cộng:           {len(channels)} kênh")
    print("="*80)
    
    # Reload channels trong sources.py để cập nhật danh sách mới
    if success_count > 0:
        print("\n🔄 Đang cập nhật danh sách kênh trong hệ thống...")
        try:
            from src.ingestion.sources import reload_channels
            updated_channels = reload_channels()
            print(f"✓ Đã cập nhật {len(updated_channels)} kênh vào hệ thống")
            print("ℹ️ Các kênh mới sẽ được fetch tự động ở lần chạy fetch tiếp theo")
        except Exception as e:
            print(f"⚠️ Lỗi reload channels: {e}")
    
    # Hiển thị danh sách topic đã map
    print("\n📋 DANH SÁCH TOPIC TIẾNG VIỆT:")
    from src.processing.category_mapper import get_all_vietnamese_topics
    for topic in get_all_vietnamese_topics():
        # Đếm số kênh cho mỗi topic
        count = sum(1 for ch in channels 
                   if map_category_to_topic(ch.get('category', '')) == topic)
        if count > 0:
            print(f"  • {topic}: {count} kênh")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto join Telegram channels from channel.json")
    parser.add_argument('--file', '-f', type=str, default='channel.json',
                       help='Đường dẫn tới file channel.json (default: channel.json)')
    parser.add_argument('--delay', '-d', type=float, default=2.0,
                       help='Thời gian chờ giữa các lần join (giây, default: 2.0)')
    
    args = parser.parse_args()
    
    asyncio.run(auto_join_channels(
        channel_json_path=args.file,
        delay=args.delay
    ))
