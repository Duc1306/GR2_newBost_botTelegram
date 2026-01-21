"""Danh sách kênh Telegram ban đầu và Twitter sources.
Lấy trực tiếp từ database (channel_metadata).
Chạy scripts/migrate_env_to_db.py để chuyển kênh từ .env vào database.
"""
from __future__ import annotations
from typing import List
from src.config import env_twitter_sources


def get_channels_from_db() -> List[str]:
    """
    Lấy danh sách kênh từ database (collection: channel_metadata)
    Trả về list username của các kênh đã join thành công
    """
    try:
        from src.db.mongo import get_db
        db = get_db()
        collection = db['channel_metadata']
        
        # Lấy tất cả kênh có trong database
        channels = collection.find({'platform': 'telegram'})
        
        # Extract username
        usernames = [ch['username'] for ch in channels if ch.get('username')]
        
        return usernames
    except Exception as e:
        print(f"⚠️ Không thể lấy kênh từ database: {e}")
        return []


# ============ TELEGRAM SOURCES ============
# Lấy trực tiếp từ database (channel_metadata)
CHANNELS: List[str] = get_channels_from_db()

if CHANNELS:
    print(f"✓ Loaded {len(CHANNELS)} channels from database")
else:
    print("⚠️ Không tìm thấy kênh nào trong database!")
    print("💡 Chạy: python scripts/migrate_env_to_db.py (nếu có kênh trong .env)")
    print("💡 Hoặc: python scripts/auto_join_channels.py (để join kênh mới)")


def reload_channels() -> List[str]:
    """
    Reload danh sách kênh từ database (dùng khi có kênh mới được thêm vào)
    
    Returns:
        List username của các kênh
    """
    global CHANNELS
    
    CHANNELS = get_channels_from_db()
    
    if CHANNELS:
        print(f"✓ Reloaded {len(CHANNELS)} channels from database")
    else:
        print("⚠️ Không tìm thấy kênh nào trong database!")
    
    return CHANNELS

# ============ TWITTER SOURCES ============
# Có thể là username (bắt đầu @) hoặc hashtag (bắt đầu #)
# Config trong file .env với TWITTER_SOURCES=@user1;@user2;#hashtag1
DEFAULT_TWITTER_SOURCES: List[str] = [
    # Để trống - config tất cả trong .env
    # Ví dụ trong .env:
    # TWITTER_SOURCES=@BBCBreaking;@Reuters;@TechCrunch;#Technology;#AI
]

TWITTER_SOURCES: List[str] = env_twitter_sources() or DEFAULT_TWITTER_SOURCES
