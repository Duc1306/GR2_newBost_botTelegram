"""Danh sách kênh Telegram ban đầu.
Có thể chỉnh sửa hoặc nạp từ ENV TELEGRAM_CHANNELS.
"""
from __future__ import annotations
from typing import List
from src.config import env_channels

# Ví dụ: thêm username kênh public (không có @ hoặc có đều được Telethon xử lý)
DEFAULT_CHANNELS: List[str] = [
    # "examplechannel1",
    # "examplechannel2",
]

CHANNELS: List[str] = env_channels() or DEFAULT_CHANNELS
