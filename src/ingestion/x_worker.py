"""X (Twitter) ingestion worker — dùng Apify thay vì Twitter API v2.

Chạy trực tiếp:
  python -m src.ingestion.x_worker --mode keyword
  python -m src.ingestion.x_worker --mode user
  python -m src.ingestion.x_worker --mode both   (mặc định)

Yêu cầu: APIFY_API_TOKEN trong .env
Sources:  X_KEYWORDS và X_USERNAMES trong .env (xem .env.example)
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, UTC
from typing import List, Optional, Tuple

from loguru import logger

from src.config import (
    APIFY_API_TOKEN,
    X_KEYWORDS,
    X_USERNAMES,
    X_FETCH_LIMIT,
)


def _get_x_users() -> List[str]:
    """
    Ưu tiên lấy tài khoản X từ MongoDB (channel_metadata, platform='twitter').
    Fallback về X_USERNAMES trong .env nếu DB trống.
    """
    try:
        from src.ingestion.sources import get_x_users_from_db
        db_users = get_x_users_from_db()
        if db_users:
            return db_users
    except Exception:
        pass
    return X_USERNAMES  # fallback
from src.processing.cleaning import clean_text
from src.processing.lang import detect_language
from src.models.post import Post, MediaItem

# ============================================================
# Actor IDs trên Apify Store
# ============================================================
# Pay-Per-Result Actor — hoạt động với Apify free credits ($5/month)
# Giá $0.25 / 1000 tweets — hỗ trợ cả keyword search và from:user
_ACTOR_KEYWORD = "kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest"
_ACTOR_USER    = _ACTOR_KEYWORD  # dùng cùng 1 Actor, khác input


# ============================================================
# Lazy-load ML classifier (giống telegram_worker.py)
# ============================================================
from pathlib import Path
from src.processing.ml_topic_classifier import MLTopicClassifier

_ml_classifier: Optional[MLTopicClassifier] = None
_ml_checked: bool = False


def _get_ml_classifier() -> Optional[MLTopicClassifier]:
    global _ml_classifier, _ml_checked
    if not _ml_checked:
        _ml_checked = True
        model_path = Path("models/topic_classifier_svm.pkl")
        if model_path.exists():
            try:
                _ml_classifier = MLTopicClassifier(model_path=str(model_path))
                logger.info("[X-Worker] ML classifier loaded OK")
            except Exception as e:
                logger.warning(f"[X-Worker] ML classifier failed to load: {e} — dùng rule-based")
        else:
            logger.info("[X-Worker] models/topic_classifier_svm.pkl chưa có — dùng rule-based")
    return _ml_classifier


# ============================================================
# Helpers — chuyển tweet thô → Post object
# ============================================================

def _parse_created_at(raw: str) -> datetime:
    """Parse ISO-8601 hoặc Twitter date string về datetime UTC."""
    if not raw:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    # Twitter legacy format: "Mon Apr 10 08:30:00 +0000 2025"
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(raw).replace(tzinfo=UTC)
    except Exception:
        return datetime.now(UTC)


def _extract_media(tweet: dict) -> List[MediaItem]:
    """Trích xuất media items từ tweet Apify (nếu có)."""
    items: List[MediaItem] = []
    for m in tweet.get("media", []) or []:
        media_type = m.get("type", "photo")   # photo | video | animated_gif
        url        = m.get("url") or m.get("previewUrl", "")
        thumb      = m.get("previewUrl") if media_type == "video" else None
        if url:
            items.append(MediaItem(type=media_type, url=url, thumbnail=thumb))
    return items


def _tweet_to_post(tweet: dict) -> Optional[Post]:
    """
    Chuyển 1 tweet thô từ Apify thành Post object.
    Trả về None nếu tweet không đủ nội dung xử lý.
    """
    raw_text = tweet.get("text") or tweet.get("full_text") or ""
    if not raw_text:
        return None

    # Làm sạch text — dùng pipeline hiện tại
    cleaned_text, links = clean_text(raw_text)
    if len(cleaned_text.strip()) < 10:
        return None

    # Thêm URL bài tweet vào links
    tweet_url = tweet.get("url") or tweet.get("twitterUrl") or ""
    if tweet_url and tweet_url not in links:
        links.append(tweet_url)

    author_obj  = tweet.get("author") or {}
    author_name = (
        author_obj.get("userName")
        or author_obj.get("username")
        or tweet.get("author_id", "unknown")
    )
    tweet_id    = str(tweet.get("id") or tweet.get("tweet_id") or tweet.get("id_str") or "0")
    created_at  = _parse_created_at(tweet.get("createdAt") or tweet.get("created_at") or "")
    media_items = _extract_media(tweet)

    post = Post.from_raw(
        platform="twitter",
        source=f"x:{author_name}",   # prefix "x:" để phân biệt với Telegram
        source_id=tweet_id,
        author=author_name,
        text=cleaned_text,
        links=links,
        media=media_items,
        created_at=created_at,
    )

    # Gán ngôn ngữ
    lang_raw = tweet.get("lang") or tweet.get("language")
    post.lang = lang_raw or detect_language(cleaned_text)

    return post


# ============================================================
# Phân loại chủ đề — tái dùng pipeline của telegram_worker
# ============================================================

def _classify_post(post: Post) -> None:
    """
    Gán topics cho post theo thứ tự ưu tiên:
    1. URL path extraction (không tốn HTTP)
    2. ML classifier (SVM)
    3. Rule-based keyword (fallback)
    """
    from src.processing.topic_classifier import classify_post_topics

    # P1: URL pattern (ưu tiên nhất — không tốn tài nguyên)
    if post.links and not post.topics:
        try:
            from src.processing.web_scraper import ArticleScraper
            category = ArticleScraper._extract_category_from_url(post.links[0])
            if category:
                topic = ArticleScraper._map_category_to_topic(category)
                if topic:
                    post.topics = [topic]
                    post.source_category = category
                    post.source_topic = topic
        except Exception:
            pass

    if post.topics:
        return  # Đã có topic từ URL

    # P2: ML classifier
    ml = _get_ml_classifier()
    ml_topic: Optional[str] = None
    ml_conf: float = 0.0
    if ml and post.text:
        try:
            ml_topic, ml_conf = ml.predict(post.text)
            if ml_conf < 0.3:
                ml_topic = None   # Tin cậy thấp → bỏ
        except Exception as e:
            logger.debug(f"[X-Worker] ML predict error: {e}")

    # P3: Rule-based keyword
    try:
        kw_result = classify_post_topics(post.text, post.lang or "en")
        kw_topic  = kw_result[0] if kw_result else None
    except Exception:
        kw_topic = None

    if ml_topic and kw_topic:
        if ml_topic == kw_topic:
            post.topics = [ml_topic]
            post.score  = ml_conf
        else:
            # Bất đồng → ưu tiên ML vì có confidence score
            post.topics = [ml_topic]
            post.score  = ml_conf
    elif ml_topic:
        post.topics = [ml_topic]
        post.score  = ml_conf
    elif kw_topic:
        post.topics = [kw_topic]
        post.score  = 0.5  # rule-based không có confidence cụ thể


# ============================================================
# Actor A — Cào theo TỪ KHÓA / HASHTAG
# ============================================================

def fetch_by_keywords(
    keywords: List[str],
    max_items: int = X_FETCH_LIMIT,
    language: str = "vi",
    query_type: str = "Latest",  # "Latest" | "Top"
) -> List[dict]:
    """
    Cào tweet theo từ khóa/hashtag.

    Args:
        keywords:   Danh sách từ khóa / hashtag, VD: ["ReactJS", "#AI", "Việt Nam công nghệ"]
        max_items:  Giới hạn tweet tổng (chia đều cho các từ khóa)
        language:   "vi", "en", hoặc "" (tất cả ngôn ngữ)
        query_type: "Latest" (mới nhất) hoặc "Top" (nổi bật)

    Returns:
        Danh sách tweet thô từ Apify
    """
    from apify_client import ApifyClient

    if not keywords:
        return []

    client     = ApifyClient(APIFY_API_TOKEN)
    per_kw     = max(1, max_items // len(keywords))  # chia đều cho từng từ khóa
    all_tweets: List[dict] = []

    for kw in keywords:
        logger.info(f"[X-Worker][Keyword] Cào '{kw}' — tối đa {per_kw} tweets")
        try:
            run_input: dict = {
                "searchTerms": [kw],
                "maxItems": max(20, per_kw),  # min 20 theo Actor requirement
                "queryType": query_type,
            }
            if language:
                run_input["lang"] = language

            run    = client.actor(_ACTOR_KEYWORD).call(run_input=run_input)
            items  = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"[X-Worker][Keyword] '{kw}' → {len(items)} tweets")
            all_tweets.extend(items)
        except Exception as e:
            logger.error(f"[X-Worker][Keyword] Lỗi khi cào '{kw}': {e}")

    return all_tweets


# ============================================================
# Actor B — Cào theo TÀI KHOẢN (timeline)
# ============================================================

def fetch_by_users(
    usernames: List[str],
    max_tweets_per_user: int = X_FETCH_LIMIT,
) -> List[dict]:
    """
    Cào tweet theo timeline tài khoản.
    để cào tweet từ timeline của từng tài khoản.

    Args:
        usernames:           Danh sách username (không cần @), VD: ["VnExpress", "tuoitrenews"]
        max_tweets_per_user: Số tweet tối đa mỗi tài khoản

    Returns:
        Danh sách tweet thô từ Apify
    """
    from apify_client import ApifyClient

    if not usernames:
        return []

    client = ApifyClient(APIFY_API_TOKEN)
    logger.info(f"[X-Worker][User] Cào timeline của: {usernames}")
    all_tweets: List[dict] = []

    for username in usernames:
        logger.info(f"[X-Worker][User] Cào @{username} — tối đa {max_tweets_per_user} tweets")
        try:
            # dùng searchTerms với Twitter advanced search operator "from:"
            run_input = {
                "searchTerms": [f"from:{username}"],
                "maxItems": max(20, max_tweets_per_user),  # min 20
                "queryType": "Latest",
            }
            run   = client.actor(_ACTOR_KEYWORD).call(run_input=run_input)
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            logger.info(f"[X-Worker][User] @{username} → {len(items)} tweets")
            all_tweets.extend(items)
        except Exception as e:
            logger.error(f"[X-Worker][User] Lỗi khi cào @{username}: {e}")

    logger.info(f"[X-Worker][User] Tổng cộng {len(all_tweets)} tweets từ {len(usernames)} tài khoản")
    return all_tweets


# ============================================================
# Smart router — tự detect loại input → đúng Actor
# ============================================================

def _route_inputs(sources: List[str]) -> Tuple[List[str], List[str]]:
    """
    Phân loại danh sách sources thành (keywords, usernames) tự động:
      - "@VnExpress"  → usernames  → Actor B (User Scraper)
      - "#ReactJS"    → keywords   → Actor A (Tweet Scraper)
      - "AI Vietnam"  → keywords   → Actor A (Tweet Scraper)

    Args:
        sources: Danh sách hỗn hợp, VD: ["@VnExpress", "#AI", "Công nghệ"]

    Returns:
        Tuple (keywords, usernames)
    """
    keywords:  List[str] = []
    usernames: List[str] = []

    for s in sources:
        s = s.strip()
        if not s:
            continue
        if s.startswith("@"):
            # @ → Actor B: cào timeline tài khoản
            usernames.append(s.lstrip("@"))
        else:
            # # hoặc từ khóa thường → Actor A: tìm kiếm tweet
            keywords.append(s)

    return keywords, usernames


async def smart_ingest(
    sources: List[str],
    max_items: int = X_FETCH_LIMIT,
    language: str = "vi",
) -> int:
    """
    Entry point thông minh. Tự phân loại sources và chọn Actor phù hợp:
      "@user"   → Actor B (User Scraper)
      "#tag"    → Actor A (Tweet Scraper)
      "keyword" → Actor A (Tweet Scraper)

    Có thể trộn lẫn trong cùng 1 lần gọi:
      smart_ingest(["@VnExpress", "#AI", "ReactJS 2026"])

    Args:
        sources:   Danh sách hỗn hợp (@user, #hashtag, keyword)
        max_items: Số tweet tối đa (per item)
        language:  Mã ngôn ngữ cho keyword search

    Returns:
        Số bài viết đã lưu vào MongoDB
    """
    if not sources:
        logger.warning("[X-Worker] smart_ingest: sources rỗng")
        return 0

    keywords, usernames = _route_inputs(sources)

    logger.info(f"[X-Worker] Smart routing:")
    logger.info(f"  Actor A (keyword) : {keywords  or '—'}")
    logger.info(f"  Actor B (user)    : {usernames or '—'}")

    return await ingest_once(
        mode="both",
        keywords=keywords   or None,
        usernames=usernames or None,
        max_items=max_items,
        language=language,
    )


# ============================================================
# Pipeline tổng hợp — xử lý + lưu MongoDB
# ============================================================

async def ingest_once(
    mode: str = "both",
    keywords: Optional[List[str]] = None,
    usernames: Optional[List[str]] = None,
    max_items: int = X_FETCH_LIMIT,
    language: str = "vi",
) -> int:
    """
    Entry point chính. Cào tweet, phân loại chủ đề, lưu MongoDB.

    Args:
        mode:      "keyword" | "user" | "both"
        keywords:  Ghi đè X_KEYWORDS từ .env nếu truyền vào
        usernames: Ghi đè X_USERNAMES từ .env nếu truyền vào
        max_items: Số tweet tối đa (per keyword hoặc per user)
        language:  Mã ngôn ngữ cho keyword search

    Returns:
        Số bài viết đã lưu vào MongoDB
    """
    if not APIFY_API_TOKEN:
        logger.error("[X-Worker] APIFY_API_TOKEN chưa được cấu hình trong .env — bỏ qua")
        return 0

    kw_list   = keywords  or X_KEYWORDS
    # Ưu tiên DB (channel_metadata platform=twitter), fallback .env
    user_list = usernames or _get_x_users()

    raw_tweets: List[dict] = []
    loop = asyncio.get_running_loop()

    # ---- Actor A: từ khóa ----
    if mode in ("keyword", "both") and kw_list:
        logger.info(f"\n[X-Worker] === Actor A: Tweet Scraper (Từ khóa) ===")
        logger.info(f"  Keywords : {kw_list}")
        logger.info(f"  Max items: {max_items} | Lang: {language}")
        kw_tweets = await loop.run_in_executor(
            None,
            lambda: fetch_by_keywords(kw_list, max_items=max_items, language=language),
        )
        raw_tweets.extend(kw_tweets)
        logger.info(f"  → {len(kw_tweets)} tweets từ keyword search")

    # ---- Actor B: tài khoản ----
    if mode in ("user", "both") and user_list:
        logger.info(f"\n[X-Worker] === Actor B: User Scraper (Tài khoản) ===")
        logger.info(f"  Users: {user_list}")
        user_tweets = await loop.run_in_executor(
            None,
            lambda: fetch_by_users(user_list, max_tweets_per_user=max_items),
        )
        raw_tweets.extend(user_tweets)
        logger.info(f"  → {len(user_tweets)} tweets từ user timelines")

    if not raw_tweets:
        logger.warning("[X-Worker] Không có tweet nào — kiểm tra lại X_KEYWORDS / X_USERNAMES trong .env")
        return 0

    logger.info(f"\n[X-Worker] Tổng cộng {len(raw_tweets)} tweet thô. Đang xử lý...")

    # ---- Chuyển sang Post object + phân loại ----
    posts: List[Post] = []
    skipped = 0
    for tweet in raw_tweets:
        post = _tweet_to_post(tweet)
        if post is None:
            skipped += 1
            continue
        _classify_post(post)
        posts.append(post)

    logger.info(f"[X-Worker] {len(posts)} posts hợp lệ | {skipped} bị bỏ qua (quá ngắn / trống)")

    # ---- Lưu vào MongoDB (tái dùng save_posts của telegram_worker) ----
    if posts:
        from src.ingestion.telegram_worker import save_posts
        await save_posts(posts, scrape_articles=False)

    return len(posts)


# ============================================================
# CLI entry point
# ============================================================

async def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="X (Twitter) ingestion worker via Apify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  # Smart router — trộn lẫn tất cả loại input
  python -m src.ingestion.x_worker --sources @VnExpress #AI "ReactJS 2026"

  # Chỉ keyword (Actor A)
  python -m src.ingestion.x_worker --mode keyword --keywords ReactJS "AI Vietnam"

  # Chỉ tài khoản (Actor B)
  python -m src.ingestion.x_worker --mode user --users VnExpress tuoitrenews
        """,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        metavar="SOURCE",
        help=(
            "Smart router — tự detect Actor dựa vào prefix: "
            "@user → Actor B, #tag / keyword → Actor A. "
            "VD: --sources @VnExpress '#AI' 'ReactJS 2026'"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["keyword", "user", "both"],
        default="both",
        help="(Bỏ qua nếu dùng --sources) Chọn Actor thủ công",
    )
    parser.add_argument("--max", type=int, default=X_FETCH_LIMIT, help="Số tweet tối đa per item")
    parser.add_argument("--lang", default="vi", help="Ngôn ngữ (vi/en/'')")
    parser.add_argument("--keywords", nargs="+", help="Truyền thẳng keywords cho Actor A")
    parser.add_argument("--users",    nargs="+", help="Truyền thẳng usernames cho Actor B")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(" X (Twitter) Worker — powered by Apify")
    logger.info("=" * 60)

    if args.sources:
        # Smart router path
        saved = await smart_ingest(
            sources=args.sources,
            max_items=args.max,
            language=args.lang,
        )
    else:
        # Manual mode path (backward compatible)
        saved = await ingest_once(
            mode=args.mode,
            keywords=args.keywords,
            usernames=args.users,
            max_items=args.max,
            language=args.lang,
        )

    logger.info(f"\n[X-Worker] Hoàn thành — {saved} bài viết đã lưu vào MongoDB")



if __name__ == "__main__":
    asyncio.run(_main())
