"""Telegram ingestion skeleton using Telethon.
Chạy: python -m src.ingestion.telegram_worker [--full]
--full: Lấy tối đa nhiều tin từ lịch sử (cho training model)
Yêu cầu: TELEGRAM_API_ID, TELEGRAM_API_HASH (và session) hoặc TELEGRAM_BOT_TOKEN.
"""
from __future__ import annotations
import asyncio
import sys
from datetime import datetime, UTC
from typing import List
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.custom.message import Message

from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING, TELEGRAM_FETCH_LIMIT
from src.ingestion.sources import CHANNELS
from src.processing.cleaning import clean_text
from src.processing.lang import detect_language
from src.processing.web_scraper import enrich_post_with_article
from src.processing.topic_classifier import classify_post_topics
from src.processing.ml_topic_classifier import MLTopicClassifier
from src.models.post import Post, MediaItem
from src.db.mongo import get_posts_collection
from pathlib import Path

# Session name (file) nếu không dùng session string
SESSION_NAME = "telegram_session"

# Chế độ lấy dữ liệu đầy đủ (nhiều hơn nhiều)
FULL_MODE_LIMIT = 1000 # Lấy tối đa 1000 tin/kênh cho training

# ML Classifier (lazy load)
_ml_classifier: MLTopicClassifier | None = None
_ml_classifier_checked: bool = False  # Flag to avoid repeated warnings


def get_ml_classifier() -> MLTopicClassifier | None:
    """Get ML classifier instance (lazy load). Returns None if not available."""
    global _ml_classifier, _ml_classifier_checked
    
    # Only check once
    if not _ml_classifier_checked:
        _ml_classifier_checked = True
        model_path = Path("models/topic_classifier_svm.pkl")
        
        if model_path.exists():
            try:
                _ml_classifier = MLTopicClassifier(model_path=str(model_path))
                print("✓ ML Topic Classifier loaded successfully")
            except Exception as e:
                print(f"  Failed to load ML classifier: {e}")
                print("   Falling back to rule-based classifier")
                _ml_classifier = None
        else:
            print("\n  ML model not found!")
            print("   → Using rule-based classifier (fallback)")
            print("   → To train ML model: python scripts/train_ml_classifier.py\n")
            _ml_classifier = None
    
    return _ml_classifier


def build_client() -> TelegramClient:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise RuntimeError("Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong .env")
    if TELEGRAM_SESSION_STRING:
        # Dạng session string nếu đã đăng nhập trước đó
        return TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    return TelegramClient(SESSION_NAME, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)

async def fetch_channel_messages(client: TelegramClient, channel: str, limit: int) -> List[Message]:
    """Lấy tin nhắn từ kênh với limit cho trước.
    Nếu limit lớn (>1000), sẽ tự động phân trang để lấy toàn bộ.
    """
    msgs: List[Message] = []
    count = 0
    async for m in client.iter_messages(channel, limit=limit):  # type: ignore
        if not getattr(m, "message", None):
            continue  # skip service messages
        msgs.append(m)
        count += 1
        # Hiển thị tiến trình mỗi 500 tin
        if count % 500 == 0:
            print(f"       Đã lấy {count} tin từ {channel}...")
    return msgs

async def process_message(m: Message, channel_name: str = "telegram") -> Post:
    raw_text = m.message or ""
    cleaned_text, links = clean_text(raw_text)
    media_items: List[MediaItem] = []
    if m.media:
        # Phân loại media type
        from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
        if isinstance(m.media, MessageMediaPhoto):
            media_items.append(MediaItem(type="photo", url="(embedded)"))
        elif isinstance(m.media, MessageMediaDocument):
            # Check if video/gif/sticker
            doc = m.media.document
            mime = getattr(doc, 'mime_type', '')
            if 'video' in mime:
                media_items.append(MediaItem(type="video", url="(embedded)"))
            elif 'image/gif' in mime:
                media_items.append(MediaItem(type="gif", url="(embedded)"))
            else:
                media_items.append(MediaItem(type="document", url="(embedded)"))
        else:
            media_items.append(MediaItem(type="other", url="(embedded)"))
    lang = detect_language(cleaned_text)
    post = Post.from_raw(
        source=channel_name,
        source_id=str(m.id),
        author=getattr(m.sender, "username", None) if m.sender else None,
        text=cleaned_text,
        links=links,
        media=media_items,
        created_at=datetime.fromtimestamp(m.date.timestamp(), UTC),
    )
    if lang:
        post.lang = lang
    
    # Try to get ground truth topic from news URL first (BEST method)
    source_topic = None
    if links:
        from src.processing.web_scraper import ArticleScraper
        try:
            # Fast extraction from URL pattern (no HTTP request needed)
            category = ArticleScraper._extract_category_from_url(links[0])
            if category:
                source_topic = ArticleScraper._map_category_to_topic(category)
                if source_topic:
                    post.topics = [source_topic]
                    # Store metadata for training validation
                    post.source_category = category
                    post.source_topic = source_topic
        except Exception:
            pass
    
    # If no ground truth from URL, use ML classifier
    if not source_topic:
        ml_classifier = get_ml_classifier()
        if ml_classifier and cleaned_text:
            try:
                predicted_topic, confidence = ml_classifier.predict(cleaned_text)
                # Chỉ lưu nếu confidence >= 0.3 (có thể điều chỉnh threshold)
                if confidence >= 0.3:
                    post.topics = [predicted_topic]
                    post.score = confidence  # Lưu confidence vào score field
            except Exception as e:
                print(f"     ML prediction error: {e}")
                # Fallback to rule-based classifier
                topics = classify_post_topics(cleaned_text, lang)
                if topics:
                    post.topics = topics
        else:
            # Fallback to rule-based classifier
            topics = classify_post_topics(cleaned_text, lang)
            if topics:
                post.topics = topics
    
    return post

async def save_posts(posts: List[Post], scrape_articles: bool = False) -> None:
    from pymongo.errors import DuplicateKeyError
    
    coll = get_posts_collection()
    if not posts:
        return
    
    # Enrich with full articles if requested
    docs = []
    scraped_count = 0
    for p in posts:
        d = p.model_dump()
        if scrape_articles and d.get('links'):
            original_keys = set(d.keys())
            d = enrich_post_with_article(d, verbose=False)
            if 'full_article' in d and 'full_article' not in original_keys:
                scraped_count += 1
        docs.append(d)
    
    inserted = 0
    updated = 0
    duplicates = 0
    
    for d in docs:
        try:
            # upsert theo id để tránh ghi đè trùng
            result = coll.update_one({"id": d["id"]}, {"$set": d}, upsert=True)
            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1
        except DuplicateKeyError:
            # Bài viết trùng dedupe_key (nội dung giống nhau), bỏ qua
            duplicates += 1
            continue
    
    status_msg = f"   💾 DB: {inserted} mới, {updated} cập nhật, {len(docs) - inserted - updated - duplicates} đã tồn tại, {duplicates} trùng lặp"
    if scrape_articles and scraped_count > 0:
        status_msg += f" | 📰 {scraped_count} bài scraped"
    print(status_msg)

def _has_external_link(links: list[str]) -> bool:
    """Kiểm tra có link ra ngoài (không phải t.me)."""
    if not links:
        return False
    for lk in links:
        if not lk:
            continue
        l = lk.lower()
        if not l.startswith("http://t.me") and not l.startswith("https://t.me"):
            return True
    return False

async def ingest_once(full_mode: bool = False, scrape_articles: bool = False, links_only: bool = False) -> None:
    """Lấy dữ liệu một lần từ tất cả kênh.
    
    Args:
        full_mode: Nếu True, lấy tối đa FULL_MODE_LIMIT tin/kênh (cho training).
                   Nếu False, lấy TELEGRAM_FETCH_LIMIT tin (mặc định 200).
        scrape_articles: Nếu True, tự động scrape nội dung đầy đủ từ links.
    """
    if not CHANNELS:
        print("Không có kênh nào trong CHANNELS. Thêm vào sources.py hoặc TELEGRAM_CHANNELS env.")
        return
    
    limit = FULL_MODE_LIMIT if full_mode else TELEGRAM_FETCH_LIMIT
    mode_str = "CHẾ ĐỘ ĐẦY ĐỦ (training)" if full_mode else "chế độ nhanh"
    scrape_str = " + SCRAPING bài báo đầy đủ" if scrape_articles else ""
    links_only_str = " + CHỈ BÀI CÓ LINK" if links_only else ""
    
    print(f"\n Bắt đầu ingestion - {mode_str}{scrape_str}{links_only_str}")
    print(f" Limit: {limit} tin/kênh | Tổng {len(CHANNELS)} kênh\n")
    
    client = build_client()
    async with client:
        all_posts: List[Post] = []
        for idx, ch in enumerate(CHANNELS, 1):
            print(f" [{idx}/{len(CHANNELS)}] Đang lấy dữ liệu từ kênh: {ch}")
            try:
                msgs = await fetch_channel_messages(client, ch, limit)
                print(f"    Lấy được {len(msgs)} tin từ {ch}")
            except FloodWaitError as e:
                print(f"    FloodWait trên kênh {ch}, chờ {e.seconds}s")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                print(f"   Lỗi kênh {ch}: {e}")
                print(f"    Kiểm tra tên kênh có đúng không (thử @{ch} trong Telegram)")
                continue
            
            # Xử lý và lưu từng batch
            batch_posts: List[Post] = []
            for m in msgs:
                try:
                    post = await process_message(m, channel_name=ch)
                    if links_only and not _has_external_link(post.links):
                        continue
                    batch_posts.append(post)
                except Exception as ex:  # pragma: no cover
                    print(f"     Lỗi xử lý message {m.id}: {ex}")
            
            # Lưu batch này ngay
            if batch_posts:
                await save_posts(batch_posts, scrape_articles=scrape_articles)
                all_posts.extend(batch_posts)
            
            print()  # Dòng trống giữa các kênh
        
        print(f"\n Hoàn tất! Tổng cộng đã xử lý {len(all_posts)} posts từ {len(CHANNELS)} kênh.")
        print(f" Dữ liệu đã được lưu vào MongoDB database: {get_posts_collection().database.name}")

if __name__ == "__main__":
    # Kiểm tra tham số --full, --scrape, --links-only
    full_mode = "--full" in sys.argv or "-f" in sys.argv
    scrape_articles = "--scrape" in sys.argv or "-s" in sys.argv
    links_only = "--links-only" in sys.argv or "-L" in sys.argv
    asyncio.run(ingest_once(full_mode, scrape_articles, links_only))
