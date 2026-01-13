"""Danh sách kênh Telegram ban đầu và Twitter sources.
Có thể chỉnh sửa hoặc nạp từ ENV.
"""
from __future__ import annotations
from typing import List
from src.config import env_channels, env_twitter_sources

# ============ TELEGRAM SOURCES ============
# Ví dụ: thêm username kênh public (không có @ hoặc có đều được Telethon xử lý)
DEFAULT_CHANNELS: List[str] = [
    # "examplechannel1",
    # "examplechannel2",
]

CHANNELS: List[str] = env_channels() or DEFAULT_CHANNELS

# ============ TWITTER SOURCES ============
# Có thể là username (bắt đầu @) hoặc hashtag (bắt đầu #)
# Config trong file .env với TWITTER_SOURCES=@user1;@user2;#hashtag1
DEFAULT_TWITTER_SOURCES: List[str] = [
    # Để trống - config tất cả trong .env
    # Ví dụ trong .env:
    # TWITTER_SOURCES=@BBCBreaking;@Reuters;@TechCrunch;#Technology;#AI
]

TWITTER_SOURCES: List[str] = env_twitter_sources() or DEFAULT_TWITTER_SOURCES
