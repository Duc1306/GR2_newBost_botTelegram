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


# =============================================================================
# CORS Configuration
# =============================================================================
_raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", "")

DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

def get_allowed_origins() -> List[str]:
    """Return CORS allowed origins: defaults + any extra from ALLOWED_ORIGINS env var."""
    extra = [o.strip() for o in _raw_allowed_origins.split(",") if o.strip()]
    return list(dict.fromkeys(DEFAULT_ORIGINS + extra))  # deduplicated, order preserved

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

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # OAuth 2.0 Client ID from Google Console

# Rate Limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# =============================================================================
# OpenAI Configuration (for AI-assisted hot topic detection)
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional – features gracefully disabled if unset
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")           # cheap & fast
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/api.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "500 MB")  # Rotate when file reaches 500MB
LOG_RETENTION = os.getenv("LOG_RETENTION", "30 days")  # Keep logs for 30 days
