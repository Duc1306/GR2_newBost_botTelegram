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

POLL_INTERVAL          = int(os.getenv("QUEUE_POLL_INTERVAL", "30"))    # seconds — pending queue poll
MAX_ATTEMPTS           = int(os.getenv("QUEUE_MAX_ATTEMPTS", "3"))
SUMMARY_POSTS          = int(os.getenv("SUMMARY_MAX_POSTS", "15"))   # posts fed to AI
REFRESH_INTERVAL       = int(os.getenv("CHANNEL_REFRESH_INTERVAL", "43200"))  # 12 hours = 2× per day
REFRESH_ON_STARTUP     = os.getenv("CHANNEL_REFRESH_ON_STARTUP", "false").lower() in {"1", "true", "yes", "on"}
SUMMARY_MIN_NEW_POSTS  = int(os.getenv("SUMMARY_MIN_NEW_POSTS", "3"))   # min new posts để trigger regenerate summary
SUMMARY_COOLDOWN_HOURS = int(os.getenv("SUMMARY_COOLDOWN_HOURS", "4"))  # giờ cooldown giữa 2 lần summary cùng channel


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
SUMMARY_DAYS = int(os.getenv("SUMMARY_DAYS", "1"))         # window (days) for AI summary — 24h by default for freshness


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

            # Extract hidden links from message entities (MessageEntityTextUrl)
            try:
                from telethon.tl.types import MessageEntityTextUrl
                if msg.entities:
                    for _ent in msg.entities:
                        if isinstance(_ent, MessageEntityTextUrl) and _ent.url:
                            if _ent.url not in links:
                                links.append(_ent.url)
            except Exception:
                pass

            # Extract link from Telegram web-page preview (MessageMediaWebPage)
            try:
                from telethon.tl.types import MessageMediaWebPage
                if msg.media and isinstance(msg.media, MessageMediaWebPage):
                    _wp_url = getattr(msg.media.webpage, 'url', None)
                    if _wp_url and _wp_url not in links:
                        links.append(_wp_url)
            except Exception:
                pass

            # Skip garbage posts: too short AND no external (non-t.me) link
            _ext_links = [
                l for l in links
                if not l.lower().startswith("http://t.me") and not l.lower().startswith("https://t.me")
            ]
            if len(text.strip()) < 15 and not _ext_links:
                continue

            dedupe_key = Post.make_dedupe_key(text, links)
            source_id = str(msg.id)
            post_id = Post.make_id(channel_username, source_id)  # "telegram:channel:msgid"

            lang = detect_language(text)
            topics = classify_post_topics(text)

            from src.processing.geo_classifier import classify_geo
            geo = await classify_geo(text, source=channel_username)

            post_doc = {
                "id": post_id,
                "platform": "telegram",
                "source": channel_username,
                "source_id": source_id,
                "text": text,
                "links": links,
                "lang": lang,
                "topics": topics,
                "geo": geo,
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

async def _batch_summarize_posts(posts_data: list[dict], loop) -> list[dict]:
    """Gọi GPT 1 call / bài để tóm tắt — đơn giản, không bao giờ bị cắt token.

    posts_data: list of {"title": str, "text": str}
    Returns: list[dict] — mỗi phần tử: {"lead": str, "body": list[str], "key_points": list[str], "thin": bool}
             Empty dict {} nếu lỗi.
    """
    import json as _json
    from src.processing.ai_topic_detector import _get_client
    from src.config import OPENAI_MODEL

    if not posts_data:
        return []

    client = _get_client()
    if not client:
        return [{}] * len(posts_data)

    SYSTEM_PROMPT = """Bạn là Tổng biên tập của một tờ báo lớn tại Việt Nam. Bạn khắt khe, chính xác và không bao giờ bịa đặt.

NHIỆM VỤ: Đọc BÀI BÁO được cung cấp, viết tóm tắt báo chí HOÀN CHỈNH, ĐẦY ĐỦ CHI TIẾT bằng tiếng Việt.

QUY TẮC BẮT BUỘC:
1. KHÔNG bịa thêm số liệu, tên người, địa điểm, sự kiện ngoài nội dung được cung cấp.
2. Nếu nội dung quá ngắn (< 50 từ): đặt "thin": true, chỉ viết "lead" 1-2 câu, còn lại để rỗng [] — nhưng vẫn có "conclusion", "sentiment", "risk_score".
3. Nếu bài có nội dung đầy đủ: "thin": false, viết đủ tất cả các trường theo định dạng.
4. Câu văn rõ ràng, khách quan, súc tích nhưng ĐẦY ĐỦ.
   Độ dài bắt buộc (khi thin=false):
   - lead: 3-4 câu, nêu rõ WHO/WHAT/WHEN/WHERE và tại sao quan trọng
   - body: 5-7 đoạn (mỗi đoạn 2-4 câu), bao quát toàn bộ nội dung bài báo
   - conclusion: 2-3 câu nhận định xu hướng tiếp theo và tác động
   - key_points: 5-7 điểm nổi bật, ưu tiên số liệu cụ thể
5. Đánh giá "sentiment": positive/negative/neutral/mixed dựa trên nội dung sự kiện.
6. Đánh giá "risk_score" từ 1-10: mức độ rủi ro/tác động tiêu cực của sự kiện đối với xã hội/kinh tế/chính trị. 1=không rủi ro, 10=rủi ro cực kỳ cao.

ĐỊNH DẠNG ĐẦU RA (Chỉ trả về JSON, không thêm văn bản nào khác):
{
  "thin": true|false,
  "lead": "3-4 câu mở đầu nêu rõ ai, cái gì, khi nào, ở đâu, và tại sao quan trọng.",
  "body": [
    "Bối cảnh và nguyên nhân dẫn đến sự kiện (số liệu cụ thể).",
    "Diễn biến chính và các mốc thời gian quan trọng.",
    "Số liệu, thống kê và bằng chứng cụ thể được đề cập trong bài.",
    "Trích dẫn phát biểu chính thức từ các bên liên quan.",
    "Phản ứng dư luận và tác động thực tế.",
    "Phân tích chuyên sâu hoặc nhận định từ chuyên gia (bỏ qua nếu không có).",
    "Tổng hợp toàn cảnh và những điểm quan trọng nhất của sự kiện."
  ],
  "conclusion": "2-3 câu nhận định xu hướng tiếp theo và ý nghĩa của sự kiện.",
  "key_points": [
    "Điểm nổi bật 1 — ưu tiên con số, tên, ngày cụ thể",
    "Điểm nổi bật 2",
    "Điểm nổi bật 3",
    "Điểm nổi bật 4",
    "Điểm nổi bật 5"
  ],
  "sentiment": "neutral|positive|negative|mixed",
  "risk_score": 5
}
KHÔNG thêm văn bản nào khác ngoài JSON."""

    def _call_one(p: dict) -> dict:
        title = (p.get("title") or "").strip()
        text = (p.get("text") or "").strip()
        if title and text and title.lower() not in text.lower()[:len(title) + 10]:
            user_msg = f"Tiêu đề: {title}\nNội dung: {text[:2000]}"
        elif text:
            user_msg = f"Nội dung: {text[:2000]}"
        else:
            user_msg = f"Tiêu đề: {title}"

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=3000,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        data = _json.loads(raw)
        return {
            "lead": (data.get("lead") or "").strip(),
            "body": [s.strip() for s in (data.get("body") or []) if s and s.strip()],
            "conclusion": (data.get("conclusion") or "").strip(),
            "key_points": [s.strip() for s in (data.get("key_points") or []) if s and s.strip()],
            "sentiment": (data.get("sentiment") or "neutral").strip(),
            "risk_score": int(data.get("risk_score") or 5),
            "thin": bool(data.get("thin", False)),
        }

    # Chạy song song tối đa 10 GPT calls cùng lúc (semaphore tránh rate-limit)
    sem = asyncio.Semaphore(10)

    async def _call_one_async(i: int, p: dict) -> tuple[int, dict]:
        async with sem:
            try:
                result = await loop.run_in_executor(None, _call_one, p)
                logger.debug(f"  summarized article {i}: thin={result['thin']}, body={len(result['body'])}s")
                return i, result
            except Exception as exc:
                logger.warning(f"_summarize_post[{i}] failed: {exc}")
                return i, {}

    tasks = [_call_one_async(i, p) for i, p in enumerate(posts_data)]
    results = await asyncio.gather(*tasks)
    out: list[dict] = [{}] * len(posts_data)
    for i, res in results:
        out[i] = res
    return out


async def _generate_summary(channel_username: str, db) -> Optional[dict]:
    """Generate a structured AI summary using summarize_cluster().

    Returns a dict with keys: title, lead, body, conclusion, key_points,
    sentiment, ai, link_posts — or None if no posts / API unavailable.
    """
    if not OPENAI_API_KEY:
        return None

    import re as _re
    from src.processing.ai_topic_detector import summarize_cluster
    posts_col = db["posts"]
    cutoff = datetime.utcnow() - timedelta(days=SUMMARY_DAYS)
    _proj = {"text": 1, "created_at": 1, "links": 1, "full_article": 1, "source": 1, "ai_summary": 1}

    if channel_username.startswith("xkw:"):
        kw = channel_username[4:]
        kw_filter = {"platform": "twitter", "text": {"$regex": _re.escape(kw), "$options": "i"}}
        recent = list(
            posts_col.find({**kw_filter, "created_at": {"$gte": cutoff}}, _proj)
            .sort("created_at", -1).limit(SUMMARY_POSTS)
        )
        if not recent:
            recent = list(posts_col.find(kw_filter, _proj).sort("created_at", -1).limit(SUMMARY_POSTS))
    else:
        recent = list(
            posts_col.find({"source": channel_username, "created_at": {"$gte": cutoff}}, _proj)
            .sort("created_at", -1).limit(SUMMARY_POSTS)
        )
        if not recent:
            recent = list(
                posts_col.find({"source": channel_username}, _proj)
                .sort("created_at", -1).limit(SUMMARY_POSTS)
            )

    if not recent:
        return None

    # Get channel display name for topic context
    channel_doc = db["channels"].find_one({"username": channel_username}, {"display_name": 1})
    topic_name = (
        (channel_doc or {}).get("display_name")
        or channel_username.replace("x:", "@").replace("xkw:", "#")
    )

    # summarize_cluster is now async — await directly
    try:
        result = await summarize_cluster(recent[:30], topic_name)
    except Exception as exc:
        logger.warning(f"summarize_cluster failed for {channel_username}: {exc}")
        return None

    result.pop("_filtered_posts", None)
    result.pop("_used_posts", None)

    # ── Step 1: Build link_posts list (15 bài hiển thị) ────────────────────
    AI_SUMMARY_LIMIT = 15   # gọi GPT cho 15 bài mới nhất
    DISPLAY_LIMIT    = 15   # tổng bài lưu vào dialog
    link_posts = []
    for i, p in enumerate(recent[:DISPLAY_LIMIT]):
        links = p.get("links") or []
        fa = p.get("full_article") or {}
        url = next((l for l in links if l.startswith("http") and "t.me" not in l), None)
        if not url:
            fa_url = fa.get("url", "")
            if fa_url and fa_url.startswith("http") and "t.me" not in fa_url:
                url = fa_url
        article_content = (fa.get("content") or fa.get("body") or "").strip()
        post_text = (p.get("text") or "").strip()
        snippet_text = article_content if len(article_content) > len(post_text) else post_text
        created = p.get("created_at")
        title = fa.get("title") or post_text[:120]
        # Reuse cached ai_summary from post doc if it has real content
        cached_ai = p.get("ai_summary") if isinstance(p.get("ai_summary"), dict) else None
        cached_valid = bool(cached_ai and (cached_ai.get("lead") or cached_ai.get("body")))
        link_posts.append({
            "_post_id": p.get("_id"),          # for cache write-back (removed before save)
            "title": title,
            "url": url,
            "source": p.get("source") or channel_username,
            "snippet": snippet_text[:1500],
            "date": created.isoformat() if created else None,
            "ai_summary": cached_ai if cached_valid else {},
            "_cached": cached_valid,            # flag to skip GPT
        })

    # ── Step 2: Scrape URLs để lấy body cho những bài chỉ có headline ───────
    # Chạy song song để không mất quá nhiều thời gian
    from src.processing.web_scraper import ArticleScraper

    def _scrape_one(lp: dict) -> dict:
        """Trả về lp đã được enrich content, hoặc nguyên gốc nếu thất bại."""
        url = lp.get("url")
        # Chỉ scrape khi snippet ≤ 200 ký tự (nghĩa là chỉ có headline)
        if not url or len((lp.get("snippet") or "")) > 200:
            return lp
        try:
            scraped = ArticleScraper.scrape_article(url)
            if scraped and scraped.get("content") and len(scraped["content"]) > 100:
                lp = dict(lp)
                lp["snippet"] = scraped["content"][:1500]
                if scraped.get("title"):
                    lp["title"] = scraped["title"]
        except Exception:
            pass
        return lp

    # Scrape song song tất cả 100 bài (concurrent, timeout per-request = 10s)
    # Chỉ scrape bài chưa có cache và snippet ngắn
    scrape_idx = [
        i for i, lp in enumerate(link_posts[:AI_SUMMARY_LIMIT])
        if not lp.get("_cached") and len((lp.get("snippet") or "")) <= 200
    ]
    try:
        scrape_results = await asyncio.gather(
            *[loop.run_in_executor(None, _scrape_one, link_posts[i]) for i in scrape_idx],
            return_exceptions=True,
        )
        for i, res in zip(scrape_idx, scrape_results):
            if isinstance(res, dict):
                link_posts[i] = res
    except Exception as exc:
        logger.warning(f"scraping gather failed: {exc}")

    # ── Step 3: GPT summarize 100 bài (đã có content từ scraping) ───────────
    # Chỉ gọi GPT cho bài chưa có cache; bài đã có cache → skip
    need_gpt_idx = [
        i for i, lp in enumerate(link_posts[:AI_SUMMARY_LIMIT])
        if not lp.get("_cached")
    ]
    link_posts_raw = [
        {"title": link_posts[i]["title"], "text": link_posts[i].get("snippet", "")[:2000]}
        for i in need_gpt_idx
    ]
    cached_count = AI_SUMMARY_LIMIT - len(need_gpt_idx)
    logger.info(f"[Summary] {channel_username}: {cached_count} cached, {len(need_gpt_idx)} need GPT")

    if link_posts_raw and OPENAI_API_KEY:
        ai_summaries = await _batch_summarize_posts(link_posts_raw, loop)
        # Write results back to link_posts and persist to posts collection
        for j, idx in enumerate(need_gpt_idx):
            s = ai_summaries[j] if j < len(ai_summaries) else {}
            link_posts[idx]["ai_summary"] = s if isinstance(s, dict) else {}
            # Cache in MongoDB post document for future calls
            post_id = link_posts[idx].get("_post_id")
            if post_id and isinstance(s, dict) and s:
                try:
                    posts_col.update_one(
                        {"_id": post_id},
                        {"$set": {"ai_summary": s}},
                    )
                except Exception:
                    pass

    # Remove internal helper fields before saving
    for lp in link_posts:
        lp.pop("_post_id", None)
        lp.pop("_cached", None)

    result["link_posts"] = link_posts

    return result


def _save_summary(channel_username: str, summary_data: dict, post_count: int, db):
    """Persist structured summary to channel_summaries collection.

    Also writes `summary_text` (plain concatenation) for backward-compat
    with older code paths that read only that field.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    summaries_col = db["channel_summaries"]

    # Build summary_text preview from per-article leads (first 3 articles)
    # This replaces the old cluster-style text shown on the outer channel card
    preview_parts: list[str] = []
    for lp in (summary_data.get("link_posts") or [])[:3]:
        ai = lp.get("ai_summary") or {}
        lead = ai.get("lead") if isinstance(ai, dict) else ""
        if lead:
            preview_parts.append(lead)
        elif lp.get("title"):
            preview_parts.append(lp["title"])
    summary_text = "\n".join(f"• {p}" for p in preview_parts) if preview_parts else ""

    summaries_col.update_one(
        {"channel_username": channel_username, "date": today},
        {
            "$set": {
                "summary_text": summary_text,
                "title": summary_data.get("title", ""),
                "lead": summary_data.get("lead", ""),
                "body": summary_data.get("body", []),
                "conclusion": summary_data.get("conclusion", ""),
                "key_points": summary_data.get("key_points", []),
                "sentiment": summary_data.get("sentiment", "neutral"),
                "risk_score": summary_data.get("risk_score", None),
                "ai": summary_data.get("ai", False),
                "link_posts": summary_data.get("link_posts", []),
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
                        if saved >= SUMMARY_MIN_NEW_POSTS:
                            # Kiểm tra cooldown: không regenerate nếu summary vừa được tạo gần đây
                            ch_doc = channels_col.find_one({"username": username}, {"last_summary_at": 1})
                            last_sum = ch_doc.get("last_summary_at") if ch_doc else None
                            cooldown_ok = (
                                last_sum is None
                                or (datetime.utcnow() - last_sum).total_seconds() >= SUMMARY_COOLDOWN_HOURS * 3600
                            )
                            if cooldown_ok:
                                logger.info(
                                    f"  @{username}: +{saved} new posts → regenerating summary"
                                )
                                summary = await _generate_summary(username, db)
                                if summary:
                                    _save_summary(username, summary, total_posts, db)
                                    channels_col.update_one(
                                        {"username": username},
                                        {"$set": {"last_summary_at": datetime.utcnow()}},
                                    )
                            else:
                                logger.debug(
                                    f"  @{username}: +{saved} new posts nhưng cooldown còn hiệu lực, bỏ qua summary."
                                )
                        elif saved > 0:
                            logger.debug(
                                f"  @{username}: +{saved} new posts (< threshold {SUMMARY_MIN_NEW_POSTS}), bỏ qua summary."
                            )
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
    By default it waits one interval before refreshing so API startup stays
    responsive. Set CHANNEL_REFRESH_ON_STARTUP=true to refresh immediately.
    """
    db = get_db()
    logger.info(f"Active-channel refresh loop started (interval: {REFRESH_INTERVAL}s, ~{REFRESH_INTERVAL//3600}h)")
    if REFRESH_ON_STARTUP:
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
