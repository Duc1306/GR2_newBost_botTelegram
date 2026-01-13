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
TELEGRAM_FETCH_LIMIT = int(os.getenv("TELEGRAM_FETCH_LIMIT", "200"))

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
