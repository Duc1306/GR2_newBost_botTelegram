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


# Ngưỡng từ khóa tần suất cao (số lần match tối thiểu để gán nhãn trực tiếp)
_KEYWORD_HIGH_FREQ_THRESHOLD = 5


def _assign_topic_cascade(post, text: str, lang: str | None) -> None:
    """
    Priority cascade for topic assignment (called when channel category and URL
    pattern are both unavailable).

    Logic:
    1. Keyword high-frequency: nếu topic dẫn đầu có score >= threshold → gán luôn.
    2. SVM + Keyword đồng thuận: nếu cả hai cùng đề xuất một topic → gán luôn.
    3. SVM + Keyword bất đồng: dùng OpenAI để phân xử. Nếu OpenAI không khả dụng
       → fallback về kết quả SVM (cao hơn keyword về độ chính xác).
    4. Chỉ có một nguồn cho kết quả → dùng nguồn đó.
    """
    from src.processing.topic_classifier import TopicClassifier

    # --- Step 1: Keyword score ---
    kw_scores = TopicClassifier.classify_with_scores(text, lang) if text else []
    kw_topic = kw_scores[0][0] if kw_scores else None
    kw_score = kw_scores[0][1] if kw_scores else 0

    if kw_topic and kw_score >= _KEYWORD_HIGH_FREQ_THRESHOLD:
        # Từ khóa xuất hiện với tần suất cao → gán nhãn trực tiếp
        post.topics = [kw_topic]
        post.score = min(kw_score / 10.0, 1.0)
        return

    # --- Step 2: SVM prediction ---
    svm_topic: str | None = None
    svm_confidence: float = 0.0
    ml_classifier = get_ml_classifier()
    if ml_classifier and text:
        try:
            svm_topic, svm_confidence = ml_classifier.predict(text)
            if svm_confidence < 0.3:
                svm_topic = None
        except Exception as e:
            print(f"     ML prediction error: {e}")

    # --- Step 3: Agreement check or OpenAI arbitration ---
    if svm_topic and kw_topic:
        if svm_topic == kw_topic:
            # Cả SVM lẫn keyword đồng thuận → kết luận ngay
            post.topics = [svm_topic]
            post.score = svm_confidence
        else:
            # Bất đồng → dùng OpenAI phân xử
            from src.processing.ai_topic_detector import arbitrate_topic
            ai_result = arbitrate_topic(text, svm_topic, kw_topic)
            if ai_result:
                post.topics = [ai_result]
                post.score = 0.85  # OpenAI arbitration → high confidence
            else:
                # OpenAI không khả dụng → ưu tiên SVM
                post.topics = [svm_topic]
                post.score = svm_confidence
    elif svm_topic:
        post.topics = [svm_topic]
        post.score = svm_confidence
    elif kw_topic:
        post.topics = [kw_topic]
        post.score = min(kw_score / 10.0, 1.0)


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
    
    # PRIORITY 1: Check channel category from database (BEST for consistent categorization)
    channel_topic = None
    try:
        from src.db.mongo import get_db
        db = get_db()
        ch_meta = db['channel_metadata'].find_one({"username": channel_name})
        if ch_meta and ch_meta.get('category'):
            channel_topic = ch_meta['category']
            post.topics = [channel_topic]
    except Exception:
        pass
    
    # PRIORITY 2: Try to get topic from news URL pattern (for channels without category)
    if not channel_topic:
        source_topic = None
        if links:
            from src.processing.web_scraper import ArticleScraper
            try:
                # Wrap blocking HTTP redirect resolution in executor
                loop = asyncio.get_running_loop()
                category = await loop.run_in_executor(
                    None, ArticleScraper._extract_category_from_url, links[0]
                )
                if category:
                    source_topic = category
                    post.topics = [source_topic]
                    post.source_topic = source_topic
            except Exception:
                pass
        
        # PRIORITY 3+: Keyword high-freq → SVM/Keyword agreement → OpenAI arbitration
        if not source_topic:
            _assign_topic_cascade(post, cleaned_text, lang)
    
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

    from pymongo import UpdateOne
    from pymongo.errors import BulkWriteError
    operations = [UpdateOne({"id": d["id"]}, {"$set": d}, upsert=True) for d in docs]
    try:
        bulk_result = coll.bulk_write(operations, ordered=False)
        inserted = bulk_result.upserted_count
        updated = bulk_result.modified_count
    except BulkWriteError as bwe:
        inserted = bwe.details.get("nUpserted", 0)
        updated = bwe.details.get("nModified", 0)
        duplicates = len(bwe.details.get("writeErrors", []))
    
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
