"""Public routes: root, health, posts feed, X live search, post summarize, topic list."""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request
from loguru import logger

from src.db.mongo import get_db
from src.api.middleware import limiter

router = APIRouter()

# In-memory cache: { normalized_keyword: fetch_timestamp }
_x_search_cache: dict = {}
_X_SEARCH_CACHE_TTL = 300  # seconds


@router.get("/", tags=["Public"])
async def root():
    """Trang chủ API."""
    return {
        "message": "🎉 MXH Aggregator API v2.0",
        "docs": "/docs",
        "security": {
            "authentication": "JWT Bearer Token or X-API-Key header",
            "login": "/auth/login",
            "default_credentials": "admin / admin123 (change in production!)",
        },
        "endpoints": {
            "auth": {"login": "/auth/login", "logout": "/auth/logout", "me": "/auth/me"},
            "core": {
                "health": "/health",
                "posts": "/posts",
                "posts_count": "/posts/count",
                "topics": "/topics",
                "stats": "/stats",
            },
            "analytics": {
                "trends": "/analytics/trends",
                "keywords": "/analytics/keywords",
                "keywords_trending": "/analytics/keywords/trending",
                "comparison": "/analytics/comparison",
                "timeline": "/analytics/timeline",
            },
            "topics": {
                "list": "/topics",
                "trending": "/topics/trending",
                "stats": "/topics/stats",
            },
        },
    }


@router.get("/health", tags=["Public"])
async def health():
    """Kiểm tra trạng thái API."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/public/posts", tags=["Public"])
@limiter.limit("200/minute")
async def get_public_posts(
    request: Request,
    q: Optional[str] = Query(None),
    keywords: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    lang: Optional[str] = Query(None),
    link_only: bool = Query(False),
    platform: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    geo: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Public news feed – no authentication required."""
    db = get_db()
    coll = db["posts"]

    query: dict = {}
    if topic:
        query["topics"] = topic
    if lang:
        query["lang"] = lang
    if link_only:
        query["links"] = {"$elemMatch": {"$regex": "^https?://", "$not": {"$regex": "t\\.me"}}}

    if platform and platform not in ("all", ""):
        if platform in ("x", "twitter"):
            query["platform"] = {"$in": ["x", "twitter"]}
        else:
            query["platform"] = platform

    if geo and geo not in ("all", ""):
        query["geo"] = geo

    if date_from or date_to:
        date_filter: dict = {}
        if date_from:
            try:
                date_filter["$gte"] = datetime.fromisoformat(date_from)
            except ValueError:
                pass
        if date_to:
            try:
                date_filter["$lte"] = datetime.fromisoformat(date_to + "T23:59:59")
            except ValueError:
                pass
        if date_filter:
            query["created_at"] = date_filter

    if q:
        query["$text"] = {"$search": q}
    elif keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if kw_list:
            query["$text"] = {"$search": " ".join(kw_list)}

    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1, "media": 1,
    }
    total = coll.count_documents(query)
    cursor = coll.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
    posts = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        posts.append(p)

    return {"posts": posts, "total": total}


@router.get("/public/x/search", tags=["Public"])
@limiter.limit("5/minute")
async def public_x_live_search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """Tìm kiếm live trên X (Twitter) qua Apify. Rate-limit: 5 req/phút/IP."""
    from src.config import APIFY_API_TOKEN as _APIFY_TOKEN

    norm_q = q.strip().lower()
    now = datetime.utcnow().timestamp()
    cached_at = _x_search_cache.get(norm_q)
    cache_hit = cached_at is not None and (now - cached_at) < _X_SEARCH_CACHE_TTL

    if not cache_hit and _APIFY_TOKEN:
        try:
            from src.ingestion.x_worker import ingest_once
            await ingest_once(mode="keyword", keywords=[q.strip()], max_items=30, language="")
            _x_search_cache[norm_q] = now
        except Exception as exc:
            logger.error(f"[public/x/search] Apify error for '{q}': {exc}")

    db = get_db()
    coll = db["posts"]
    query_filter: dict = {"platform": {"$in": ["x", "twitter"]}}
    if q:
        query_filter["$text"] = {"$search": q.strip()}

    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1, "media": 1,
    }
    total = coll.count_documents(query_filter)
    cursor = coll.find(query_filter, projection).sort("created_at", -1).skip(skip).limit(limit)
    posts = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        posts.append(p)

    return {"posts": posts, "total": total, "live": not cache_hit, "q": q.strip()}


@router.post("/public/posts/{post_id}/summarize", tags=["Public"])
@limiter.limit("30/minute")
async def public_summarize_post(post_id: str, request: Request):
    """Tóm tắt 1 bài viết công khai bằng GPT. Rate-limit: 30 req/phút/IP."""
    import json as _json
    from src.config import OPENAI_API_KEY as _OPENAI_API_KEY, OPENAI_MODEL as _OPENAI_MODEL

    if not _OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI chưa được cấu hình.")

    db = get_db()
    post = db["posts"].find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài viết.")

    cached = post.get("ai_summary")
    if isinstance(cached, dict) and (cached.get("lead") or cached.get("body")):
        return cached

    fa = post.get("full_article") or {}
    article_content = (fa.get("content") or fa.get("body") or "").strip()
    post_text = (post.get("text") or "").strip()

    if len(article_content) < 200:
        external_link = next(
            (l for l in (post.get("links") or [])
             if l and l.startswith("http") and "t.me" not in l),
            None,
        )
        if external_link:
            try:
                from src.processing.web_scraper import ArticleScraper
                scraped = await asyncio.to_thread(ArticleScraper.scrape_article, external_link)
                if scraped:
                    scraped_content = (scraped.get("content") or "").strip()
                    if len(scraped_content) > len(article_content):
                        article_content = scraped_content
                        if not fa.get("title") and scraped.get("title"):
                            fa = {"title": scraped["title"]}
                        db["posts"].update_one(
                            {"id": post_id},
                            {"$set": {"full_article": {
                                "title": scraped.get("title", ""),
                                "content": scraped_content,
                                "url": external_link,
                            }}},
                        )
            except Exception as _e:
                logger.warning(f"public scrape failed post={post_id}: {_e}")

    snippet = article_content if len(article_content) > len(post_text) else post_text
    title = (fa.get("title") or post_text[:120]).strip()

    if title and snippet and title.lower() not in snippet.lower()[:len(title) + 10]:
        user_msg = f"Tiêu đề: {title}\nNội dung: {snippet[:2000]}"
    elif snippet:
        user_msg = f"Nội dung: {snippet[:2000]}"
    else:
        user_msg = f"Tiêu đề: {title}"

    platform = (post.get("platform") or "").lower()
    from src.api.channels import _SINGLE_POST_SYSTEM_PROMPT, _X_POST_SYSTEM_PROMPT
    system_prompt = _X_POST_SYSTEM_PROMPT if platform in ("x", "twitter") else _SINGLE_POST_SYSTEM_PROMPT

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=_OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=1500,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        data = _json.loads(raw)
        ai_summary = {
            "lead": (data.get("lead") or "").strip(),
            "body": [s.strip() for s in (data.get("body") or []) if s and s.strip()],
            "conclusion": (data.get("conclusion") or "").strip(),
            "key_points": [s.strip() for s in (data.get("key_points") or []) if s and s.strip()],
            "sentiment": (data.get("sentiment") or "neutral").strip(),
            "risk_score": int(data.get("risk_score") or 5),
            "thin": bool(data.get("thin", False)),
        }
    except Exception as exc:
        logger.error(f"public_summarize_post GPT error post={post_id}: {exc}")
        raise HTTPException(status_code=502, detail=f"GPT lỗi: {exc}")

    if ai_summary.get("lead") or ai_summary.get("body"):
        db["posts"].update_one({"id": post_id}, {"$set": {"ai_summary": ai_summary}})

    return ai_summary


# ML topic → display colour mapping (shared)
_TOPIC_COLORS: dict[str, str] = {
    "Crypto": "#f59e0b",
    "Kinh tế": "#10b981",
    "Công nghệ": "#3b82f6",
    "Chính trị": "#8b5cf6",
    "Thế giới": "#6366f1",
    "Pháp luật": "#ef4444",
    "Thể thao": "#22d3ee",
    "Giải trí": "#ec4899",
    "Stock": "#84cc16",
    "Ô tô - Xe máy": "#f97316",
    "Sức khỏe - Y tế": "#14b8a6",
    "Bất động sản": "#a16207",
    "Khoa học": "#0ea5e9",
    "Giáo dục": "#7c3aed",
    "Du lịch": "#059669",
    "Thời trang": "#db2777",
}


@router.get("/public/post-topics", tags=["Public"])
@limiter.limit("120/minute")
async def get_public_post_topics(request: Request):
    """Return distinct ML-classified topic categories that appear in posts with external links."""
    db = get_db()
    posts_coll = db["posts"]

    pipeline = [
        {"$match": {
            "links": {"$elemMatch": {"$regex": "^https?://", "$not": {"$regex": "t\\.me"}}},
            "topics": {"$exists": True, "$ne": []},
        }},
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 30},
    ]
    raw = list(posts_coll.aggregate(pipeline))

    topics = [
        {
            "name": t["_id"],
            "slug": (
                t["_id"].lower()
                .replace(" ", "-")
                .replace("&", "and")
                .replace("đ", "d")
            ),
            "count": t["count"],
            "color": _TOPIC_COLORS.get(t["_id"], "#6b7280"),
        }
        for t in raw
        if t["_id"]
    ]
    return {"topics": topics}


# ─── Daily Stats ─────────────────────────────────────────────────────────────

@router.get("/public/stats/daily", tags=["Public"])
@limiter.limit("60/minute")
async def get_daily_stats(
    request: Request,
    days: int = Query(30, ge=1, le=90),
):
    """Thống kê số bài viết và số chủ đề mỗi ngày trong N ngày gần nhất."""
    db = get_db()
    posts_coll = db["posts"]

    start_date = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "posts": {"$sum": 1},
            "all_topics": {"$push": "$topics"},
            "platforms": {"$push": "$platform"},
        }},
        {"$sort": {"_id": 1}},
    ]
    results = list(posts_coll.aggregate(pipeline))

    daily = []
    for r in results:
        unique_topics: set = set()
        for topic_list in r["all_topics"]:
            for t in (topic_list or []):
                unique_topics.add(t)

        platforms_count: dict = {}
        for p in r["platforms"]:
            if p:
                platforms_count[p] = platforms_count.get(p, 0) + 1

        daily.append({
            "date": r["_id"],
            "posts": r["posts"],
            "topics": len(unique_topics),
            "by_platform": platforms_count,
        })

    total_posts = sum(d["posts"] for d in daily)
    return {
        "daily": daily,
        "days": days,
        "total_posts": total_posts,
        "avg_per_day": round(total_posts / len(daily), 1) if daily else 0,
    }


# ─── Geo Distribution ────────────────────────────────────────────────────────

_GEO_REGION_EMOJI = {
    "Việt Nam": "🇻🇳",
    "Mỹ": "🇺🇸",
    "Trung Quốc": "🇨🇳",
    "Nga": "🇷🇺",
    "Nhật Bản": "🇯🇵",
    "Hàn Quốc": "🇰🇷",
    "Châu Âu": "🇪🇺",
    "Trung Đông": "🌙",
    "Đông Nam Á": "🌏",
    "Toàn cầu": "🌍",
    "Khác": "📍",
}

_GEO_REGION_COLOR = {
    "Việt Nam": "#ef4444",
    "Mỹ": "#3b82f6",
    "Trung Quốc": "#f59e0b",
    "Nga": "#8b5cf6",
    "Nhật Bản": "#ec4899",
    "Hàn Quốc": "#10b981",
    "Châu Âu": "#6366f1",
    "Trung Đông": "#f97316",
    "Đông Nam Á": "#14b8a6",
    "Toàn cầu": "#22d3ee",
    "Khác": "#6b7280",
}


@router.get("/public/stats/geo", tags=["Public"])
@limiter.limit("60/minute")
async def get_geo_stats(
    request: Request,
    days: int = Query(7, ge=1, le=30),
):
    """Phân phối bài viết theo khu vực địa lý trong N ngày gần nhất."""
    db = get_db()
    posts_coll = db["posts"]

    start_date = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {
            "created_at": {"$gte": start_date},
            "geo": {"$exists": True, "$nin": [None, ""]},
        }},
        {"$group": {"_id": "$geo", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    results = list(posts_coll.aggregate(pipeline))

    total = sum(r["count"] for r in results)
    geo = [
        {
            "region": r["_id"],
            "count": r["count"],
            "percent": round(r["count"] / total * 100, 1) if total else 0,
            "emoji": _GEO_REGION_EMOJI.get(r["_id"], "📍"),
            "color": _GEO_REGION_COLOR.get(r["_id"], "#6b7280"),
        }
        for r in results
        if r["_id"]
    ]

    return {
        "geo": geo,
        "total": total,
        "days": days,
        "has_data": total > 0,
    }
