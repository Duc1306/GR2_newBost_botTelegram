"""Central config loader."""
from __future__ import annotations
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "newsbot")

# Telegram Configuration
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")  # khi dùng user login

# số lượng message tối đa lấy mỗi lần cho 1 channel
TELEGRAM_FETCH_LIMIT = int(os.getenv("TELEGRAM_FETCH_LIMIT", "2000"))

# kênh tiêu chuẩn sẽ định nghĩa ở sources.py; cho phép override bằng ENV nếu muốn
RAW_CHANNELS = os.getenv("TELEGRAM_CHANNELS")  # dạng: channel1;channel2;channel3

def env_channels() -> List[str]:
    if not RAW_CHANNELS:
        return []
    return [c.strip() for c in RAW_CHANNELS.split(";") if c.strip()]

# Twitter Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# số lượng tweets tối đa lấy mỗi lần
TWITTER_FETCH_LIMIT = int(os.getenv("TWITTER_FETCH_LIMIT", "100"))

# Twitter accounts/hashtags để theo dõi
RAW_TWITTER_SOURCES = os.getenv("TWITTER_SOURCES")  # dạng: @user1;@user2;#hashtag1

def env_twitter_sources() -> List[str]:
    if not RAW_TWITTER_SOURCES:
        return []
    return [s.strip() for s in RAW_TWITTER_SOURCES.split(";") if s.strip()]

# =============================================================================
# Security & Authentication Configuration
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-2026")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

# Admin Credentials (simple auth - for demo purposes)
# In production, use hashed passwords in database
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production!

# API Key for external clients (optional)
API_KEY = os.getenv("API_KEY")  # If set, clients can use this instead of JWT

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/api.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "500 MB")  # Rotate when file reaches 500MB
LOG_RETENTION = os.getenv("LOG_RETENTION", "30 days")  # Keep logs for 30 days
