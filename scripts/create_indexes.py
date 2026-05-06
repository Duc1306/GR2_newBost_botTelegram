"""Tạo indexes cho MongoDB collections.
Chạy một lần sau khi thiết lập DB.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pymongo.errors import OperationFailure
from src.db.mongo import get_posts_collection, get_db


def _safe_create(col, keys, **kwargs):
    """Tạo index, bỏ qua nếu index đã tồn tại (dù khác tên)."""
    try:
        col.create_index(keys, **kwargs)
    except OperationFailure as e:
        # code 85 = IndexOptionsConflict (same key, different name/options)
        # code 86 = IndexKeySpecsConflict
        if e.code in (85, 86):
            pass  # index already exists — no action needed
        else:
            raise


def create_indexes():
    posts = get_posts_collection()
    db = get_db()

    # ── posts collection ──
    _safe_create(posts, "id", unique=True)
    _safe_create(posts, "dedupe_key", unique=True)
    _safe_create(posts, [("created_at", -1)])
    _safe_create(posts, "source")
    _safe_create(posts, "topics")
    _safe_create(posts, "platform")
    _safe_create(posts, "lang")
    _safe_create(posts, [("platform", 1), ("created_at", -1)])
    _safe_create(posts, [("topics", 1), ("created_at", -1)])
    _safe_create(posts, [("source", 1), ("created_at", -1)])
    _safe_create(posts, [("text", "text")])

    # ── channel_summaries collection ──
    summaries = db["channel_summaries"]
    _safe_create(summaries, [("channel_username", 1), ("date", -1)])

    # ── user_channels collection ──
    user_channels = db["user_channels"]
    _safe_create(user_channels, [("user_id", 1), ("channel_username", 1)], unique=True)

    # ── channels collection ──
    channels = db["channels"]
    _safe_create(channels, "username", unique=True)
    _safe_create(channels, [("status", 1), ("platform", 1)])

    # ── users collection ──
    users = db["users"]
    _safe_create(users, "username", unique=True)
    _safe_create(users, "phone_number")
    _safe_create(users, "email")
    _safe_create(users, "telegram_user_id")

    # ── channel_metadata collection ──
    channel_meta = db["channel_metadata"]
    _safe_create(channel_meta, "platform")

    # ── notifications collection ──
    notifications = db["notifications"]
    _safe_create(notifications, [("user", 1), ("created_at", -1)])
    _safe_create(notifications, [("user", 1), ("read", 1)])

    # ── user_settings collection ──
    user_settings = db["user_settings"]
    _safe_create(user_settings, "username", unique=True)

    # ── hot_topics collection ──
    hot_topics = db["hot_topics"]
    _safe_create(hot_topics, [("slug", 1), ("active", 1)])

    # ── keyword_trends collection ──
    kw_trends = db["keyword_trends"]
    _safe_create(kw_trends, [("date", 1), ("total_count", -1)])
    _safe_create(kw_trends, [("date", 1), ("trend_velocity", -1)])

    # ── cache collections ──
    _safe_create(db["hotnews_v2_cache"], "key", unique=True)
    # TTL index: tự xóa cache entries sau 3 ngày
    _safe_create(db["hotnews_v2_cache"], [("expires_at", 1)], expireAfterSeconds=0, name="hotnews_v2_cache_ttl")
    _safe_create(db["hotnews_summary_cache"], "key", unique=True)

    # ── pending_channels collection ──
    _safe_create(db["pending_channels"], "channel_username", unique=True)

if __name__ == "__main__":
    create_indexes()
