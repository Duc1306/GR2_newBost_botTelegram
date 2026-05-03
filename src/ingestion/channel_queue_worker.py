"""
Channel Queue Worker
====================
Reads the `pending_channels` MongoDB collection and processes each channel:
  1. Join/access the Telegram channel (via Telethon)
  2. Fetch recent messages (up to TELEGRAM_FETCH_LIMIT)
  3. Save raw posts to the `posts` collection
  4. Generate an AI summary via OpenAI and save to `channel_summaries`
  5. Update the `channels` collection status → active

Run:
    python -m src.ingestion.channel_queue_worker

The worker loops forever, sleeping POLL_INTERVAL seconds between scans.
"""
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timedelta, UTC
from typing import Optional

from loguru import logger

from src.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_SESSION_STRING,
    TELEGRAM_FETCH_LIMIT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from src.db.mongo import get_db
from src.models.post import Post
from src.processing.cleaning import clean_text
from src.processing.lang import detect_language
from src.processing.topic_classifier import classify_post_topics

POLL_INTERVAL    = int(os.getenv("QUEUE_POLL_INTERVAL", "30"))    # seconds — pending queue poll
MAX_ATTEMPTS     = int(os.getenv("QUEUE_MAX_ATTEMPTS", "3"))
SUMMARY_POSTS    = int(os.getenv("SUMMARY_MAX_POSTS", "100"))  # posts fed to AI
REFRESH_INTERVAL = int(os.getenv("CHANNEL_REFRESH_INTERVAL", "43200"))  # 12 hours = 2× per day


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

def _build_client():
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise RuntimeError("Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH")
    if TELEGRAM_SESSION_STRING:
        return TelegramClient(
            StringSession(TELEGRAM_SESSION_STRING),
            int(TELEGRAM_API_ID),
            TELEGRAM_API_HASH,
        )
    return TelegramClient("telegram_session", int(TELEGRAM_API_ID), TELEGRAM_API_HASH)


FETCH_DAYS = int(os.getenv("TELEGRAM_FETCH_DAYS", "7"))   # only fetch posts from last N days
SUMMARY_DAYS = int(os.getenv("SUMMARY_DAYS", "7"))         # window (days) for AI summary generation — independent of FETCH_DAYS


async def _fetch_and_store(client, channel_username: str, db, min_id: int = 0) -> int:
    """Fetch messages from a Telegram channel and upsert into `posts`. Returns count of new posts saved.

    Args:
        min_id: if > 0, only fetch messages with id > min_id (incremental refresh).
                if 0, fetch up to TELEGRAM_FETCH_LIMIT messages within the last FETCH_DAYS days.
    """
    from telethon.errors import FloodWaitError
    posts_col = db["posts"]
    saved = 0

    try:
        entity = await client.get_entity(channel_username)
    except Exception as exc:
        raise RuntimeError(f"Không thể truy cập kênh @{channel_username}: {exc}") from exc

    display_name = getattr(entity, "title", None) or channel_username

    # Date cutoff for initial fetch (ignored when min_id is set)
    cutoff_date = datetime.now(UTC) - timedelta(days=FETCH_DAYS) if min_id == 0 else None

    iter_kwargs = {"limit": TELEGRAM_FETCH_LIMIT}
    if min_id > 0:
        iter_kwargs["min_id"] = min_id
    elif cutoff_date:
        iter_kwargs["offset_date"] = None  # let date filtering happen in loop

    async for msg in client.iter_messages(entity, **iter_kwargs):
        try:
            # Skip messages older than cutoff on initial fetch
            if cutoff_date and msg.date and msg.date < cutoff_date:
                break  # iter_messages returns newest-first, so we can break early

            raw_text = getattr(msg, "message", None) or ""
            if not isinstance(raw_text, str):
                raw_text = str(raw_text) if raw_text else ""
            if not raw_text.strip():
                continue

            text, _links = clean_text(raw_text)
            if not text:
                continue

            links = _links or []
            dedupe_key = Post.make_dedupe_key(text, links)
            source_id = str(msg.id)
            post_id = Post.make_id(channel_username, source_id)  # "telegram:channel:msgid"

            lang = detect_language(text)
            topics = classify_post_topics(text)

            post_doc = {
                "id": post_id,
                "platform": "telegram",
                "source": channel_username,
                "source_id": source_id,
                "text": text,
                "links": links,
                "lang": lang,
                "topics": topics,
                "created_at": msg.date.replace(tzinfo=None) if msg.date else datetime.utcnow(),
                "fetched_at": datetime.utcnow(),
                "dedupe_key": dedupe_key,
            }
            # upsert by dedupe_key (content hash) — idempotent, works across id format changes
            result = posts_col.update_one(
                {"dedupe_key": dedupe_key},
                {"$setOnInsert": post_doc},
                upsert=True,
            )
            if result.upserted_id:
                saved += 1
        except Exception as exc:
            logger.warning(f"Skipped message {getattr(msg, 'id', '?')} in {channel_username}: {exc}")

    # Update display_name in channels collection
    db["channels"].update_one(
        {"username": channel_username},
        {"$set": {"display_name": display_name}},
    )
    return saved


# ---------------------------------------------------------------------------
# AI Summary helpers
# ---------------------------------------------------------------------------

async def _generate_summary(channel_username: str, db) -> Optional[str]:
    """Generate an AI summary: 1 bullet per post, in Vietnamese."""
    if not OPENAI_API_KEY:
        return None

    import re as _re
    posts_col = db["posts"]
    cutoff = datetime.utcnow() - timedelta(days=SUMMARY_DAYS)

    # xkw: channels don't have matching source field — query by keyword text
    if channel_username.startswith("xkw:"):
        kw = channel_username[4:]
        kw_filter = {"platform": "twitter", "text": {"$regex": _re.escape(kw), "$options": "i"}}
        recent = list(
            posts_col.find({**kw_filter, "created_at": {"$gte": cutoff}}, {"text": 1, "created_at": 1})
            .sort("created_at", -1)
            .limit(SUMMARY_POSTS)
        )
        if not recent:
            recent = list(
                posts_col.find(kw_filter, {"text": 1})
                .sort("created_at", -1)
                .limit(SUMMARY_POSTS)
            )
    else:
        recent = list(
            posts_col.find(
                {"source": channel_username, "created_at": {"$gte": cutoff}},
                {"text": 1, "created_at": 1},
            )
            .sort("created_at", -1)
            .limit(SUMMARY_POSTS)
        )
        if not recent:
            # Fall back to last N posts regardless of date
            recent = list(
                posts_col.find({"source": channel_username}, {"text": 1})
                .sort("created_at", -1)
                .limit(SUMMARY_POSTS)
            )

    if not recent:
        return None

    n_posts = len(recent)

    # Build numbered post list so AI can map 1-to-1
    numbered = "\n\n".join(
        f"[{i+1}] {p['text'].strip()}"
        for i, p in enumerate(recent)
        if p.get("text")
    )
    if len(numbered) > 24000:
        numbered = numbered[:24000]

    # Dynamic token budget: ~80 tokens per bullet, min 600
    max_tokens = min(max(n_posts * 80, 600), 4000)

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Bạn là trợ lý tóm tắt tin tức từ kênh Telegram @{channel_username}. "
                        f"Dưới đây là {n_posts} bài viết được đánh số [1] đến [{n_posts}]. "
                        f"Hãy viết ĐÚNG {n_posts} dòng tóm tắt bằng tiếng Việt, "
                        "mỗi dòng là 1 bullet (•) tương ứng với bài cùng số thứ tự. "
                        "Mỗi bullet phải là 1 câu đầy đủ, súc tích, bao hàm trọn vẹn nội dung bài đó "
                        "(gồm: sự kiện chính, số liệu, kết quả nếu có). "
                        "KHÔNG gộp, KHÔNG bỏ bài nào, KHÔNG thêm tiêu đề hay giải thích."
                    ),
                },
                {"role": "user", "content": numbered},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning(f"OpenAI summary failed for {channel_username}: {exc}")
        return None


def _save_summary(channel_username: str, summary_text: str, post_count: int, db):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    summaries_col = db["channel_summaries"]
    summaries_col.update_one(
        {"channel_username": channel_username, "date": today},
        {
            "$set": {
                "summary_text": summary_text,
                "post_count": post_count,
                "generated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Main worker loop
# ---------------------------------------------------------------------------

async def process_one(pending_doc: dict, db):
    """Process a single pending channel entry."""
    ch_username = pending_doc["channel_username"]
    pending_col = db["pending_channels"]
    channels_col = db["channels"]
    loop = asyncio.get_running_loop()

    attempts = pending_doc.get("attempts", 0) + 1
    await loop.run_in_executor(None, lambda: pending_col.update_one(
        {"_id": pending_doc["_id"]},
        {"$set": {"attempts": attempts, "last_attempt": datetime.utcnow()}},
    ))

    try:
        client = _build_client()
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("Telegram session chưa được xác thực. Chạy scripts/create_session.py trước.")
            await client.disconnect()
            return

        logger.info(f"Processing channel: @{ch_username}")
        saved = await _fetch_and_store(client, ch_username, db)
        logger.info(f"  Saved {saved} new posts from @{ch_username}")

        await client.disconnect()

        # Generate AI summary
        summary = await _generate_summary(ch_username, db)
        total_posts = await loop.run_in_executor(
            None, lambda: db["posts"].count_documents({"source": ch_username})
        )
        if summary:
            _save_summary(ch_username, summary, total_posts, db)
            logger.info(f"  Summary saved for @{ch_username}")

        # Mark channel as active
        await loop.run_in_executor(None, lambda: channels_col.update_one(
            {"username": ch_username},
            {
                "$set": {
                    "status": "active",
                    "processed_at": datetime.utcnow(),
                    "error_message": None,
                    "post_count": total_posts,
                }
            },
        ))

        # Remove from pending queue
        await loop.run_in_executor(None, lambda: pending_col.delete_one({"_id": pending_doc["_id"]}))
        logger.info(f"  @{ch_username} → active ✓")

    except Exception as exc:
        logger.error(f"Failed to process @{ch_username}: {exc}")
        if attempts >= MAX_ATTEMPTS:
            await loop.run_in_executor(None, lambda: channels_col.update_one(
                {"username": ch_username},
                {"$set": {"status": "error", "error_message": str(exc)}},
            ))
            await loop.run_in_executor(None, lambda: pending_col.delete_one({"_id": pending_doc["_id"]}))
            logger.warning(f"  @{ch_username} marked as error after {attempts} attempts.")
        else:
            await loop.run_in_executor(None, lambda: pending_col.update_one(
                {"_id": pending_doc["_id"]},
                {"$set": {"next_attempt": datetime.utcnow() + timedelta(minutes=5)}},
            ))


async def run_worker():
    """Main worker loop — polls `pending_channels` every POLL_INTERVAL seconds."""
    db = get_db()
    logger.info(f"Channel Queue Worker started (poll interval: {POLL_INTERVAL}s)")

    while True:
        try:
            now = datetime.utcnow()
            # Only pick entries whose next_attempt time has passed (or not set)
            cursor = db["pending_channels"].find({
                "$or": [
                    {"next_attempt": {"$exists": False}},
                    {"next_attempt": {"$lte": now}},
                ]
            })
            pending = list(cursor)

            if pending:
                logger.info(f"Found {len(pending)} pending channel(s)")
                for doc in pending:
                    await process_one(doc, db)
            else:
                logger.debug("No pending channels.")

        except Exception as exc:
            logger.exception(f"Worker loop error: {exc}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_worker())


# ---------------------------------------------------------------------------
# Active-channel periodic refresh (imported by FastAPI lifespan)
# ---------------------------------------------------------------------------

async def refresh_active_channels(db) -> None:
    """Fetch new posts from all `active` channels and re-generate summaries if new data found.
    
    - platform=telegram : dùng Telethon (như cũ)
    - platform=twitter  : dùng Apify x_worker (mới)
    """
    channels_col = db["channels"]
    active = list(channels_col.find({"status": "active"}, {"username": 1, "platform": 1, "last_apify_fetch": 1}))
    if not active:
        logger.debug("Refresh: no active channels.")
        return

    # Tách Telegram và X
    tg_channels = [ch for ch in active if ch.get("platform", "telegram") == "telegram"]
    x_channels  = [ch for ch in active if ch.get("platform") == "twitter"]

    logger.info(f"Refreshing {len(tg_channels)} Telegram + {len(x_channels)} X channel(s)…")

    # ── Telegram ──────────────────────────────────────────────
    if tg_channels:
        client = _build_client()
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.error("Refresh: Telegram session not authorized. Skipping Telegram.")
            else:
                for ch in tg_channels:
                    username = ch["username"]
                    try:
                        cutoff = datetime.utcnow() - timedelta(days=FETCH_DAYS)
                        channels_col.database["posts"].delete_many({
                            "source": username,
                            "created_at": {"$lt": cutoff},
                        })
                        saved = await _fetch_and_store(client, username, db)
                        total_posts = db["posts"].count_documents({"source": username})
                        channels_col.update_one(
                            {"username": username},
                            {"$set": {"post_count": total_posts}},
                        )
                        if saved > 0:
                            logger.info(f"  @{username}: +{saved} new posts → regenerating summary")
                            summary = await _generate_summary(username, db)
                            if summary:
                                _save_summary(username, summary, total_posts, db)
                    except Exception as exc:
                        logger.warning(f"  Refresh failed for @{username}: {exc}")
        finally:
            await client.disconnect()

    # ── X / Twitter ───────────────────────────────────────────
    # X channels (xkw: keyword và x: account) không auto-refresh.
    # Dữ liệu được cập nhật khi user bấm "Tóm tắt lại" (_run_summarize).
    if x_channels:
        logger.debug(f"  X refresh: skipped ({len(x_channels)} channels — on-demand only)")


async def run_refresh_loop() -> None:
    """Background loop: refresh all active channels every REFRESH_INTERVAL seconds.
    Runs immediately on startup so data is collected right away, then repeats every
    REFRESH_INTERVAL seconds (default 43200 = 2× per day).
    """
    db = get_db()
    logger.info(f"Active-channel refresh loop started (interval: {REFRESH_INTERVAL}s, ~{REFRESH_INTERVAL//3600}h)")
    # Run immediately on startup — don't wait for the first interval to pass
    try:
        await refresh_active_channels(db)
    except Exception as exc:
        logger.exception(f"Refresh loop error (initial run): {exc}")
    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        try:
            await refresh_active_channels(db)
        except Exception as exc:
            logger.exception(f"Refresh loop error: {exc}")
