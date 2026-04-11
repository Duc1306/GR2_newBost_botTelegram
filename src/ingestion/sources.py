"""Danh sách nguồn thu thập dữ liệu từ database (Telegram + X/Twitter).

Collection duy nhất: channel_metadata
  platform = "telegram" → kênh Telegram
  platform = "twitter"  → tài khoản X cần theo dõi

Chạy scripts/migrate_env_to_db.py để chuyển kênh Telegram từ .env vào database.
Chạy scripts/seed_x_sources.py    để seed tài khoản X mẫu vào database.
"""
from __future__ import annotations
from typing import List, TypedDict


class XSource(TypedDict):
    username: str       # Tên tài khoản (không có @)
    category: str       # Chủ đề chính, VD: "Công nghệ", "Kinh tế"
    is_active: bool


# ============================================================
# Telegram
# ============================================================

def get_channels_from_db() -> List[str]:
    """Lấy list username kênh Telegram đang active từ channel_metadata."""
    try:
        from src.db.mongo import get_db
        db = get_db()
        channels = db['channel_metadata'].find(
            {'platform': 'telegram', 'is_active': {'$ne': False}}
        )
        usernames = [ch['username'] for ch in channels if ch.get('username')]
        return usernames
    except Exception as e:
        print(f"⚠️  Không thể lấy kênh Telegram từ database: {e}")
        return []


# ============================================================
# X / Twitter — cùng collection channel_metadata, platform="twitter"
# ============================================================

def get_x_users_from_db() -> List[str]:
    """
    Lấy list username tài khoản X đang active từ channel_metadata.
    Trả về list username thuần (không có @) để truyền thẳng vào Apify Actor B.
    """
    try:
        from src.db.mongo import get_db
        db = get_db()
        sources = db['channel_metadata'].find(
            {'platform': 'twitter', 'is_active': {'$ne': False}}
        )
        usernames = [s['username'] for s in sources if s.get('username')]
        return usernames
    except Exception as e:
        print(f"⚠️  Không thể lấy X sources từ database: {e}")
        return []


# ============================================================
# Module-level singletons (load 1 lần khi import)
# ============================================================

# Telegram
CHANNELS: List[str] = get_channels_from_db()
if CHANNELS:
    print(f"✓ Loaded {len(CHANNELS)} Telegram channels from database")
else:
    print("⚠️  Không tìm thấy kênh Telegram nào!")
    print("💡  Chạy: python scripts/migrate_env_to_db.py")

# X / Twitter users
X_USERS: List[str] = get_x_users_from_db()
if X_USERS:
    print(f"✓ Loaded {len(X_USERS)} X/Twitter accounts from database")
else:
    print("⚠️  Không tìm thấy X account nào!")
    print("💡  Chạy: python scripts/seed_x_sources.py")


# ============================================================
# Reload helpers (dùng khi admin thêm source mới qua API)
# ============================================================

def reload_channels() -> List[str]:
    """Reload kênh Telegram từ database."""
    global CHANNELS
    CHANNELS = get_channels_from_db()
    print(f"✓ Reloaded {len(CHANNELS)} Telegram channels")
    return CHANNELS


def reload_x_users() -> List[str]:
    """Reload tài khoản X từ database."""
    global X_USERS
    X_USERS = get_x_users_from_db()
    print(f"✓ Reloaded {len(X_USERS)} X/Twitter accounts")
    return X_USERS
