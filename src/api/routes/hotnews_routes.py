"""Hot news routes: hot-topics, hotnews clusters, summaries, audio."""
from __future__ import annotations
import asyncio
import base64
import io
import math
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from src.db.mongo import get_db
from src.api.middleware import limiter
from src.api.routes.tts_routes import _generate_tts_bytes

router = APIRouter(tags=["Public"])

# ---------------------------------------------------------------------------
# In-memory hotnews cache
# TTL matches bucket_size: 1h for 24h window, 2h for 48h, 3h for 72h+.
# ---------------------------------------------------------------------------
_hotnews_mem: dict[str, dict] = {}
_hotnews_locks: dict[str, asyncio.Lock] = {}


def _hotnews_mem_ttl(hours: int) -> timedelta:
    if hours <= 24:
        return timedelta(hours=1)
    elif hours <= 48:
        return timedelta(hours=2)
    return timedelta(hours=3)


def _cleanup_hotnews_cache() -> None:
    now = datetime.utcnow()
    expired = []
    for k, v in list(_hotnews_mem.items()):
        try:
            hours = int(k.split(":")[1])
        except (IndexError, ValueError):
            hours = 72
        if now - v["ts"] > _hotnews_mem_ttl(hours):
            expired.append(k)
    for k in expired:
        _hotnews_mem.pop(k, None)
        _hotnews_locks.pop(k, None)


def _get_hotnews_lock(key: str) -> asyncio.Lock:
    _cleanup_hotnews_cache()
    if key not in _hotnews_locks:
        _hotnews_locks[key] = asyncio.Lock()
    return _hotnews_locks[key]


# ---------------------------------------------------------------------------
# Default hot topics seed data
# ---------------------------------------------------------------------------
DEFAULT_HOT_TOPICS = [
    {
        "slug": "iran-israel-conflict",
        "name": "⚡ Iran – Israel",
        "description": "Xung đột Iran - Israel và khu vực Trung Đông",
        "keywords": ["iran", "israel", "tehran", "idf", "irgc", "netanyahu", "khamenei",
                     "airstrike", "missile strike", "không kích", "tên lửa", "hezbollah",
                     "tel aviv", "jerusalem", "mossad"],
        "color": "#ef4444",
        "priority": 1,
        "active": True,
    },
    {
        "slug": "ukraine-war",
        "name": "🇺🇦 Chiến tranh Ukraine",
        "description": "Chiến tranh Nga – Ukraine và phản ứng quốc tế",
        "keywords": ["ukraine", "russia", "zelensky", "putin", "kyiv", "moscow",
                     "nato", "donbas", "crimea", "kherson", "bakhmut", "volodymyr",
                     "nga", "ukraine war", "ukrainian"],
        "color": "#3b82f6",
        "priority": 2,
        "active": True,
    },
    {
        "slug": "middle-east-gaza",
        "name": "🕌 Gaza & Trung Đông",
        "description": "Tình hình dải Gaza và khu vực Trung Đông",
        "keywords": ["gaza", "hamas", "west bank", "ramallah", "rafah", "palestin",
                     "houthi", "yemen", "lebanon", "syria", "jordan", "saudi arabia",
                     "ceasefire", "ngừng bắn"],
        "color": "#f59e0b",
        "priority": 3,
        "active": True,
    },
    {
        "slug": "us-politics",
        "name": "🇺🇸 Chính trị Mỹ",
        "description": "Chính trị, kinh tế và đối ngoại Hoa Kỳ",
        "keywords": ["trump", "biden", "harris", "congress", "white house",
                     "democrat", "republican", "senate", "tariff", "sanction",
                     "america", "washington"],
        "color": "#8b5cf6",
        "priority": 4,
        "active": True,
    },
    {
        "slug": "china-asia",
        "name": "🌏 Trung Quốc & Châu Á",
        "description": "Địa chính trị Trung Quốc, Đài Loan và khu vực",
        "keywords": ["china", "taiwan", "xi jinping", "taipei", "pla",
                     "south china sea", "biển đông", "trung quốc", "đài loan",
                     "north korea", "kim jong un", "dprk", "triều tiên"],
        "color": "#ec4899",
        "priority": 5,
        "active": True,
    },
    {
        "slug": "ai-technology",
        "name": "🤖 AI & Công nghệ",
        "description": "Trí tuệ nhân tạo và công nghệ mới",
        "keywords": ["ai", "artificial intelligence", "chatgpt", "openai", "nvidia",
                     "gemini", "llm", "deepseek", "trí tuệ nhân tạo", "machine learning",
                     "tech giant", "silicon valley", "chip"],
        "color": "#06b6d4",
        "priority": 6,
        "active": True,
    },
    {
        "slug": "world-economy",
        "name": "📈 Kinh tế quốc tế",
        "description": "Kinh tế và tài chính toàn cầu",
        "keywords": ["recession", "inflation", "fed", "interest rate", "gdp",
                     "stock market", "dollar", "trade war", "tariff", "khủng hoảng",
                     "imf", "world bank", "economy", "financial"],
        "color": "#10b981",
        "priority": 7,
        "active": True,
    },
    {
        "slug": "climate-disaster",
        "name": "🌡️ Thiên tai & Khí hậu",
        "description": "Biến đổi khí hậu và thiên tai toàn cầu",
        "keywords": ["earthquake", "flood", "typhoon", "hurricane", "wildfire",
                     "tsunami", "climate change", "global warming", "tornado",
                     "động đất", "lũ lụt", "bão", "thiên tai"],
        "color": "#84cc16",
        "priority": 8,
        "active": True,
    },
]

# ML topic → display colour mapping
_ML_TOPIC_COLORS = {
    "Thể thao": "#2563eb",
    "Công nghệ": "#7c3aed",
    "Tin tức & Truyền thông": "#dc2626",
    "Giải trí": "#d97706",
    "Giáo dục": "#059669",
    "Kinh tế": "#0891b2",
    "Kinh doanh & Khởi nghiệp": "#0d9488",
    "Sức khỏe": "#16a34a",
    "Chính trị": "#b91c1c",
    "Pháp luật": "#7c2d12",
    "Du lịch": "#0284c7",
    "Khoa học": "#6d28d9",
    "Ô tô - Xe máy": "#92400e",
    "Crypto": "#f59e0b",
    "Thế giới": "#be123c",
}


def _ml_topic_slug(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# ---------------------------------------------------------------------------
# Background TTS pre-generation
# ---------------------------------------------------------------------------

async def _bg_pregenerate_audio(slug: str, summary_doc: dict) -> None:
    """Pre-generate TTS audio right after a summary is saved."""
    try:
        db = get_db()
        audio_cache = db["hotnews_audio_cache"]
        now = datetime.utcnow()

        expires_at = summary_doc.get("expires_at")
        summary_bucket = expires_at.strftime("%Y%m%d%H%M") if expires_at else "x"
        cache_key = f"audio:{slug}:{summary_bucket}"

        if audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}}, {"_id": 1}):
            return

        parts = []
        for field in ("title", "lead"):
            v = summary_doc.get(field, "")
            if v:
                parts.append(v)
        for para in (summary_doc.get("body") or []):
            if para:
                parts.append(para)
        conclusion = summary_doc.get("conclusion", "")
        if conclusion:
            parts.append(conclusion)
        key_points = summary_doc.get("key_points") or []
        if key_points:
            parts.append("Các điểm chính: " + ". ".join(key_points))

        tts_text = ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())
        if len(tts_text) > 7000:
            tts_text = tts_text[:7000]
        if not tts_text:
            return

        audio_bytes = await _generate_tts_bytes(tts_text)
        if not audio_bytes:
            return

        audio_cache.update_one(
            {"key": cache_key},
            {"$set": {
                "key": cache_key,
                "slug": slug,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                "created_at": now,
                "expires_at": now + timedelta(hours=2),
            }},
            upsert=True,
        )
        logger.info("_bg_pregenerate_audio: cached %d bytes for slug=%s", len(audio_bytes), slug)
    except Exception as exc:
        logger.warning("_bg_pregenerate_audio failed slug=%s: %s", slug, exc)


# ---------------------------------------------------------------------------
# Core hotnews pipeline
# ---------------------------------------------------------------------------

async def _compute_hotnews_clusters(db, hours: int, now: datetime, cache_key: str) -> list[dict]:
    """
    Core hotnews pipeline: fetch posts → DBSCAN+GPT clustering → ML fallback → cache.
    Caller MUST hold _get_hotnews_lock(cache_key) before calling.
    """
    from src.processing.ai_topic_detector import (
        filter_relevant_posts, discover_hot_events,
        cluster_and_summarize as _cas,
    )

    posts_coll = db["posts"]
    cache_coll = db["hotnews_v2_cache"]
    since = now - timedelta(hours=hours)

    projection = {
        "_id": 1, "text": 1, "source": 1, "created_at": 1,
        "links": 1, "topics": 1, "lang": 1, "full_article": 1,
        "channel_username": 1,
    }

    # ── Step 1: Fetch posts ───────────────────────────────────────────────────
    _EMBED_CAP = 450
    WINDOW_SLICE_HOURS = 12
    window_slices = max(1, min(8, math.ceil(hours / WINDOW_SLICE_HOURS)))
    per_slice_limit = max(40, math.ceil(_EMBED_CAP / window_slices))
    all_posts: list[dict] = []
    seen_ids: set = set()

    slice_h = math.ceil(hours / window_slices)
    for i in range(window_slices):
        slice_end = now - timedelta(hours=i * slice_h)
        slice_start = now - timedelta(hours=(i + 1) * slice_h)
        if slice_start < since:
            slice_start = since
        for p in posts_coll.find(
            {"created_at": {"$gte": slice_start, "$lt": slice_end}}, projection,
        ).sort("created_at", -1).limit(per_slice_limit):
            pid = str(p["_id"])
            if pid not in seen_ids:
                seen_ids.add(pid)
                p["_id"] = pid
                all_posts.append(p)

    if len(all_posts) > _EMBED_CAP:
        by_slice: list[list[dict]] = [[] for _ in range(window_slices)]
        for p in all_posts:
            created = p.get("created_at")
            if not created:
                by_slice[0].append(p)
                continue
            age_hours = max(0.0, (now - created).total_seconds() / 3600)
            idx = min(window_slices - 1, int(age_hours // slice_h))
            by_slice[idx].append(p)

        balanced: list[dict] = []
        slice_quota = max(1, _EMBED_CAP // window_slices)
        for bucket in by_slice:
            with_links = [p for p in bucket if p.get("links")]
            no_links = [p for p in bucket if not p.get("links")]
            balanced.extend((with_links + no_links)[:slice_quota])

        if len(balanced) < _EMBED_CAP:
            used = {p["_id"] for p in balanced}
            remainder = [p for p in all_posts if p["_id"] not in used]
            with_links = [p for p in remainder if p.get("links")]
            no_links = [p for p in remainder if not p.get("links")]
            balanced.extend((with_links + no_links)[:_EMBED_CAP - len(balanced)])

        logger.info(
            "hotnews: balanced cap all_posts %d→%d across %d slices",
            len(all_posts), len(balanced[:_EMBED_CAP]), window_slices,
        )
        all_posts = balanced[:_EMBED_CAP]

    clusters: list[dict] = []

    # ── Step 2: Embedding clustering (PRIMARY) ────────────────────────────────
    async def _build_cluster(ev: dict) -> dict | None:
        ev_posts = ev.get("posts", [])
        if len(ev_posts) < 2:
            return None

        try:
            _anchor = next((p for p in ev_posts if p.get("links")), ev_posts[0])
            _fa = _anchor.get("full_article") or {}
            _anchor_text = (
                (_fa.get("title") or "") + " " + (_fa.get("body") or _anchor.get("text") or "")
            )[:600].strip()
            _filter_query = _anchor_text if len(_anchor_text) > 60 else ev["name"]
            event_filtered = await filter_relevant_posts(
                ev_posts, topic_name=_filter_query, threshold=0.58, top_k=15,
            )
            if len(event_filtered) < 2:
                logger.info(
                    "_build_cluster: dropped loose cluster %r (%d→%d)",
                    ev["name"], len(ev_posts), len(event_filtered),
                )
                return None
            if "_ai_score" in event_filtered[0] and event_filtered[0].get("_ai_score", 0) < 0.58:
                logger.info(
                    "_build_cluster: dropped low-confidence cluster %r top_score=%.3f",
                    ev["name"], event_filtered[0].get("_ai_score", 0),
                )
                return None
        except Exception as _fe:
            logger.warning("_build_cluster: filter failed: %s", _fe)
            event_filtered = ev_posts[:15]

        filtered = sorted(event_filtered, key=lambda p: (not bool(p.get("links")), 0))
        filtered = filtered[:15]
        for p in filtered:
            p.pop("_emb", None)
            p.pop("_ai_score", None)

        latest = max(
            (p.get("created_at") for p in filtered if p.get("created_at")),
            default=None,
        )
        latest_str = latest.isoformat() if hasattr(latest, "isoformat") else ""
        headline = (
            (filtered[0].get("full_article") or {}).get("title")
            or (filtered[0].get("text") or "")[:120]
        )
        cl_slug = _ml_topic_slug(ev["name"])
        cluster = {
            "slug": cl_slug,
            "name": ev["name"],
            "description": ev.get("description", ""),
            "color": ev.get("color", "#be123c"),
            "post_count": len(filtered),
            "posts_with_links": len([p for p in filtered if any(
                l.startswith("http") and "t.me" not in l
                for l in (p.get("links") or [])
            )]),
            "latest_at": latest_str,
            "headline": headline,
            "posts": filtered,
            "source": "embedding_cluster",
        }

        try:
            summary_coll = db["hotnews_summary_cache"]
            summary_cache_key = f"{cl_slug}:{hours}:v2"
            existing = summary_coll.find_one(
                {"key": summary_cache_key, "expires_at": {"$gt": now}},
                {"_id": 0, "title": 1},
            )
            if not existing:
                async def _bg_summary(
                    _filtered=list(filtered),
                    _ev_name=ev["name"],
                    _slug=cl_slug,
                ):
                    try:
                        _result = await _cas(_filtered, topic_name=_ev_name)
                        _gpt_validated = _result.pop("_filtered_posts", None) or _filtered
                        _link_posts = []
                        for _p in _gpt_validated:
                            _links = _p.get("links") or []
                            _fa2 = _p.get("full_article") or {}
                            _url = next(
                                (l for l in _links if l.startswith("http") and "t.me" not in l),
                                None,
                            )
                            if not _url:
                                _fa_url = _fa2.get("url", "")
                                if _fa_url and _fa_url.startswith("http") and "t.me" not in _fa_url:
                                    _url = _fa_url
                            _link_posts.append({
                                "title": _fa2.get("title") or (_p.get("text") or "")[:120],
                                "url": _url,
                                "source": _p.get("source") or _p.get("channel_username") or "",
                                "snippet": (_p.get("text") or "")[:200],
                            })
                        _expires = datetime.utcnow() + timedelta(minutes=30)
                        _saved_summary = {
                            **_result,
                            "key": summary_cache_key,
                            "post_count": len(_gpt_validated),
                            "link_posts": _link_posts,
                            "expires_at": _expires,
                        }
                        summary_coll.update_one(
                            {"key": summary_cache_key},
                            {"$set": _saved_summary},
                            upsert=True,
                        )
                        db["hotnews_audio_cache"].delete_many(
                            {"key": re.compile(f"^audio:{re.escape(_slug)}")}
                        )
                        logger.info("_bg_summary: done slug=%s posts=%d", _slug, len(_gpt_validated))
                        asyncio.create_task(_bg_pregenerate_audio(_slug, _saved_summary))
                    except Exception as _exc:
                        logger.warning("_bg_summary failed for %s: %s", _slug, _exc)

                asyncio.create_task(_bg_summary())
        except Exception as exc:
            logger.warning("_build_cluster: summary setup failed for %s: %s", cl_slug, exc)

        return cluster

    events = await discover_hot_events(all_posts, max_events=8)
    build_results = await asyncio.gather(
        *[_build_cluster(ev) for ev in events],
        return_exceptions=True,
    )
    for cl in build_results:
        if isinstance(cl, Exception):
            logger.warning("_build_cluster error: %s", cl)
            continue
        if cl and not any(c["slug"] == cl["slug"] for c in clusters):
            clusters.append(cl)

    # ── Step 3: ML-topic velocity fallback ───────────────────────────────────
    if len(clusters) < 4:
        velocity_pipeline = [
            {"$match": {"created_at": {"$gte": since}, "topics": {"$exists": True, "$ne": []}}},
            {"$unwind": "$topics"},
            {"$group": {
                "_id": "$topics",
                "count": {"$sum": 1},
                "with_links": {"$sum": {"$cond": [
                    {"$gt": [{"$size": {"$ifNull": ["$links", []]}}, 0]}, 1, 0,
                ]}},
                "latest": {"$max": "$created_at"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 8},
        ]
        trending = list(posts_coll.aggregate(velocity_pipeline))
        existing_slugs = {c["slug"] for c in clusters}

        ml_subcluster_tasks = []
        for item in trending:
            if len(clusters) + len(ml_subcluster_tasks) >= 8:
                break
            topic_name = item["_id"]
            if not topic_name:
                continue
            slug = _ml_topic_slug(topic_name)
            if slug in existing_slugs:
                continue

            raw_posts = list(
                posts_coll.find({"created_at": {"$gte": since}, "topics": topic_name}, projection)
                .limit(60)
            )
            for p in raw_posts:
                p["_id"] = str(p["_id"])

            has_link = sorted([p for p in raw_posts if p.get("links")],
                              key=lambda p: p.get("created_at") or datetime.min, reverse=True)
            no_link = sorted([p for p in raw_posts if not p.get("links")],
                             key=lambda p: p.get("created_at") or datetime.min, reverse=True)
            sorted_posts = has_link + no_link

            # Do not publish a broad ML topic as one "event". First split it
            # into specific embedding/GPT event clusters, then reuse the same
            # strict cluster builder as the primary path.
            topic_events = await discover_hot_events(
                sorted_posts,
                max_events=max(1, min(3, 8 - len(clusters) - len(ml_subcluster_tasks))),
            )
            for ev in topic_events:
                ev["_broad_topic"] = topic_name
                ev.setdefault("color", _ML_TOPIC_COLORS.get(topic_name, "#6b7280"))
                ev_slug = _ml_topic_slug(ev.get("name", ""))
                if ev_slug and ev_slug not in existing_slugs:
                    ml_subcluster_tasks.append(_build_cluster(ev))
                    existing_slugs.add(ev_slug)
                if len(clusters) + len(ml_subcluster_tasks) >= 8:
                    break

        if ml_subcluster_tasks:
            ml_results = await asyncio.gather(*ml_subcluster_tasks, return_exceptions=True)
            for cl in ml_results:
                if isinstance(cl, Exception):
                    logger.warning("ml topic subcluster build error: %s", cl)
                    continue
                if cl and not any(c["slug"] == cl["slug"] for c in clusters):
                    cl["source"] = "ml_topic_subcluster"
                    clusters.append(cl)

    # ── Step 4: Clean + timestamp ─────────────────────────────────────────────
    clusters = [cl for cl in clusters if cl.get("slug") and cl.get("name")]
    for cl in clusters:
        cl["first_seen_at"] = now.isoformat()

    # ── Step 5: Persist to cache ──────────────────────────────────────────────
    expires_at = now + timedelta(days=3)
    cache_coll.update_one(
        {"key": cache_key},
        {"$set": {"key": cache_key, "clusters": clusters, "created_at": now, "expires_at": expires_at}},
        upsert=True,
    )
    logger.info("_compute_hotnews_clusters: done key=%s clusters=%d", cache_key, len(clusters))
    return clusters


async def _bg_ensure_hotnews_cached(hours: int, cache_key: str, now: datetime) -> None:
    """Background task: compute and cache a new hotnews bucket (stale-while-revalidate)."""
    lock = _get_hotnews_lock(cache_key)
    if lock.locked():
        return
    async with lock:
        db = get_db()
        fresh = db["hotnews_v2_cache"].find_one({"key": cache_key}, {"_id": 1})
        if fresh:
            return
        try:
            clusters = await _compute_hotnews_clusters(db, hours, now, cache_key)
            since = now - timedelta(hours=hours)
            result = {"clusters": clusters, "since": since.isoformat(), "hours": hours, "cached": False}
            _hotnews_mem[cache_key] = {"result": result, "ts": now}
            logger.info("_bg_ensure_hotnews_cached: done key=%s clusters=%d", cache_key, len(clusters))
        except Exception as exc:
            logger.exception("_bg_ensure_hotnews_cached failed key=%s: %s", cache_key, exc)


async def _hotnews_precompute_worker() -> None:
    """Background worker: pre-warm the 24h hotnews cache every 5 minutes."""
    await asyncio.sleep(120)
    while True:
        try:
            now = datetime.utcnow()
            db = get_db()
            cache_coll = db["hotnews_v2_cache"]
            for hours in [24]:
                bucket_size = 1
                bucket_hour = (now.hour // bucket_size) * bucket_size
                cache_key = f"hotnews_kw:{hours}:{now.strftime('%Y%m%d')}{bucket_hour:02d}"

                if not cache_coll.find_one({"key": cache_key}, {"_id": 1}):
                    logger.info("hotnews warmer: computing missing bucket %s", cache_key)
                    asyncio.create_task(_bg_ensure_hotnews_cached(hours, cache_key, now))
                    continue

                mins_past = now.minute % (bucket_size * 60)
                mins_left = (bucket_size * 60) - mins_past
                if mins_left <= 10:
                    next_now = now + timedelta(minutes=mins_left + 1)
                    next_bh = (next_now.hour // bucket_size) * bucket_size
                    next_key = f"hotnews_kw:{hours}:{next_now.strftime('%Y%m%d')}{next_bh:02d}"
                    if not cache_coll.find_one({"key": next_key}, {"_id": 1}):
                        logger.info("hotnews warmer: pre-computing next bucket %s", next_key)
                        asyncio.create_task(_bg_ensure_hotnews_cached(hours, next_key, next_now))
        except Exception as exc:
            logger.exception("hotnews precompute worker error: %s", exc)
        await asyncio.sleep(300)


# =============================================================================
# Public Hot Topics Endpoints
# =============================================================================

@router.get("/public/hot-topics")
async def get_public_hot_topics():
    """Return active hot topics list – no authentication required."""
    db = get_db()
    coll = db["hot_topics"]
    topics = list(coll.find({"active": True}, {"_id": 0}).sort("priority", 1))
    if not topics:
        return {"topics": DEFAULT_HOT_TOPICS, "seeded": False}
    return {"topics": topics, "seeded": True}


@router.get("/public/hot-topics/{slug}/posts")
@limiter.limit("200/minute")
async def get_public_hot_topic_posts(
    request: Request,
    slug: str,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Return posts matching a hot topic's keywords – no authentication required."""
    db = get_db()
    hot_topics_coll = db["hot_topics"]
    posts_coll = db["posts"]

    topic_doc = hot_topics_coll.find_one({"slug": slug, "active": True}, {"_id": 0})
    if not topic_doc:
        topic_doc = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)
    if not topic_doc:
        raise HTTPException(status_code=404, detail="Hot topic not found")

    keywords = topic_doc.get("keywords", [])
    if not keywords:
        return {"topic": topic_doc, "posts": [], "total": 0, "skip": skip, "limit": limit}

    query = {"$text": {"$search": " ".join(keywords)}}
    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1,
    }
    cursor = posts_coll.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
    posts = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        posts.append(p)

    total = posts_coll.count_documents(query)
    return {"topic": topic_doc, "posts": posts, "total": total, "skip": skip, "limit": limit}


@router.get("/public/hot-topics/{slug}/posts/ai")
@limiter.limit("30/minute")
async def get_hot_topic_posts_ai(
    request: Request,
    slug: str,
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """Like /public/hot-topics/{slug}/posts but re-ranks using OpenAI embeddings."""
    from src.processing.ai_topic_detector import score_posts_by_embedding
    db = get_db()
    hot_coll = db["hot_topics"]
    posts_coll = db["posts"]

    topic_doc = hot_coll.find_one({"slug": slug, "active": True}, {"_id": 0})
    if not topic_doc:
        topic_doc = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)
    if not topic_doc:
        raise HTTPException(status_code=404, detail="Hot topic not found")

    keywords = topic_doc.get("keywords", [])
    if not keywords:
        return {"topic": topic_doc, "posts": [], "total": 0, "ai_ranked": False}

    keyword_query = {"$or": [{"text": {"$regex": kw, "$options": "i"}} for kw in keywords]}
    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1,
    }

    fetch_limit = min((skip + limit) * 3, 150)
    cursor = posts_coll.find(keyword_query, projection).sort("created_at", -1).limit(fetch_limit)
    candidates = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        candidates.append(p)

    query_text = (
        f"{topic_doc['name']}. {topic_doc.get('description', '')}. "
        f"Keywords: {', '.join(keywords[:15])}"
    )
    ranked = await score_posts_by_embedding(candidates, query_text)
    page = ranked[skip: skip + limit]
    ai_ranked = any("_ai_score" in p for p in page)

    total = posts_coll.count_documents(keyword_query)
    return {
        "topic": topic_doc,
        "posts": page,
        "total": total,
        "ai_ranked": ai_ranked,
        "skip": skip,
        "limit": limit,
    }


@router.get("/public/hotnews")
@limiter.limit("120/minute")
async def get_public_hotnews(
    request: Request,
    hours: int = Query(48, ge=1, le=168),
):
    """Return hot-news clusters driven by embedding-based event clustering."""
    db = get_db()
    cache_coll = db["hotnews_v2_cache"]
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)

    if hours <= 24:
        bucket_size = 1
    elif hours <= 48:
        bucket_size = 2
    else:
        bucket_size = 3
    bucket_hour = (now.hour // bucket_size) * bucket_size
    cache_key = f"hotnews_kw:{hours}:{now.strftime('%Y%m%d')}{bucket_hour:02d}"

    # L1: in-memory cache
    mem = _hotnews_mem.get(cache_key)
    if mem and (now - mem["ts"]) < _hotnews_mem_ttl(hours):
        return {**mem["result"], "cached": True}

    # L2: MongoDB cache
    cached = cache_coll.find_one({"key": cache_key})
    if cached and cached.get("clusters"):
        result = {"clusters": cached["clusters"], "since": since.isoformat(), "hours": hours, "cached": True}
        _hotnews_mem[cache_key] = {"result": result, "ts": datetime.utcnow()}
        return result

    # L3: compute — stale-while-revalidate
    lock = _get_hotnews_lock(cache_key)
    if lock.locked():
        prev = cache_coll.find_one(
            {"clusters": {"$exists": True, "$ne": []}},
            sort=[("created_at", -1)],
        )
        if prev and prev.get("clusters"):
            return {"clusters": prev["clusters"], "since": since.isoformat(),
                    "hours": hours, "cached": True, "refreshing": True}

    prev_cached = cache_coll.find_one(
        {
            "key": re.compile(f"^hotnews_kw:{hours}:"),
            "clusters": {"$exists": True, "$ne": []},
        },
        sort=[("created_at", -1)],
    )
    if prev_cached and prev_cached.get("clusters") and prev_cached.get("key") != cache_key:
        asyncio.create_task(_bg_ensure_hotnews_cached(hours, cache_key, now))
        return {
            "clusters": prev_cached["clusters"],
            "since": since.isoformat(),
            "hours": hours,
            "cached": True,
            "refreshing": True,
        }

    # Cold start — must compute synchronously
    async with lock:
        mem = _hotnews_mem.get(cache_key)
        if mem and (datetime.utcnow() - mem["ts"]) < _hotnews_mem_ttl(hours):
            return {**mem["result"], "cached": True}
        fresh = cache_coll.find_one({"key": cache_key})
        if fresh and fresh.get("clusters"):
            result = {"clusters": fresh["clusters"], "since": since.isoformat(), "hours": hours, "cached": True}
            _hotnews_mem[cache_key] = {"result": result, "ts": datetime.utcnow()}
            return result

        clusters = await _compute_hotnews_clusters(db, hours, now, cache_key)
        result = {"clusters": clusters, "since": since.isoformat(), "hours": hours, "cached": False}
        _hotnews_mem[cache_key] = {"result": result, "ts": now}
        return result


@router.post("/public/hotnews/{slug}/summary")
@limiter.limit("30/minute")
async def get_hotnews_summary(
    request: Request,
    slug: str,
    hours: int = Query(48, ge=1, le=168),
):
    """Use OpenAI to summarise all recent posts for a hot-topic cluster."""
    from src.processing.ai_topic_detector import cluster_and_summarize

    db = get_db()
    cache_coll = db["hotnews_summary_cache"]
    posts_coll = db["posts"]

    def _extract_link_posts(posts: list[dict]) -> list[dict]:
        result = []
        for p in posts:
            links = p.get("links") or []
            fa = p.get("full_article") or {}
            url = next((l for l in links if l.startswith("http") and "t.me" not in l), None)
            if not url:
                fa_url = fa.get("url", "")
                if fa_url and fa_url.startswith("http") and "t.me" not in fa_url:
                    url = fa_url
            title = fa.get("title") or (p.get("text") or "")[:120]
            snippet = (p.get("text") or "")[:200]
            source = p.get("source") or p.get("channel_username") or ""
            result.append({"title": title, "url": url, "source": source, "snippet": snippet})
        return result

    cache_key = f"{slug}:{hours}:v2"
    cached = cache_coll.find_one({"key": cache_key})
    if cached and cached.get("expires_at") and cached["expires_at"] > datetime.utcnow():
        if cached.get("post_count", 0) <= 1:
            cached = None
    if cached and cached.get("expires_at") and cached["expires_at"] > datetime.utcnow():
        return {
            "slug": slug,
            "title": cached.get("title", ""),
            "lead": cached.get("lead", ""),
            "body": cached.get("body", []),
            "conclusion": cached.get("conclusion", ""),
            "key_points": cached.get("key_points", []),
            "sentiment": cached.get("sentiment", "neutral"),
            "ai": cached.get("ai", False),
            "cached": True,
            "post_count": cached.get("post_count", 0),
            "link_posts": cached.get("link_posts", []),
        }

    since = datetime.utcnow() - timedelta(hours=hours)
    proj = {"_id": 0, "text": 1, "full_article": 1, "source": 1, "links": 1, "created_at": 1}

    ml_topic_name = next(
        (name for name in _ML_TOPIC_COLORS if _ml_topic_slug(name) == slug), None,
    )

    if ml_topic_name:
        cutoff = datetime.utcnow() - timedelta(hours=max(hours, 3))
        hn_cached = db["hotnews_v2_cache"].find_one(
            {"clusters.slug": slug, "created_at": {"$gte": cutoff}},
            sort=[("created_at", -1)],
        )
        cluster_posts = None
        if hn_cached:
            cl = next((c for c in (hn_cached.get("clusters") or []) if c["slug"] == slug), None)
            if cl and cl.get("posts"):
                cluster_posts = cl["posts"][:15]

        if cluster_posts:
            posts = cluster_posts
        else:
            raw = list(
                posts_coll.find({"created_at": {"$gte": since}, "topics": ml_topic_name}, proj)
                .sort("created_at", -1).limit(20)
            )
            has_link = [p for p in raw if p.get("links")]
            no_link = [p for p in raw if not p.get("links")]
            posts = (has_link + no_link)[:15]
        topic_display_name = ml_topic_name
    else:
        hot_topics_coll = db["hot_topics"]
        topic_doc = hot_topics_coll.find_one({"slug": slug, "active": True}, {"_id": 0})
        if not topic_doc:
            topic_doc = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)

        if not topic_doc:
            cutoff = datetime.utcnow() - timedelta(hours=max(hours, 6))
            hn_cached = db["hotnews_v2_cache"].find_one(
                {"clusters.slug": slug, "created_at": {"$gte": cutoff}},
                sort=[("created_at", -1)],
            )
            if hn_cached:
                cluster = next((c for c in (hn_cached.get("clusters") or []) if c["slug"] == slug), None)
                if cluster:
                    posts = cluster.get("posts", [])[:15]
                    topic_display_name = cluster["name"]
                    result = await cluster_and_summarize(posts, topic_display_name)
                    result.pop("_filtered_posts", None)
                    link_posts = _extract_link_posts(posts)
                    expires_at = datetime.utcnow() + timedelta(minutes=30)
                    cache_coll.update_one(
                        {"key": cache_key},
                        {"$set": {**result, "key": cache_key, "post_count": len(posts),
                                  "link_posts": link_posts, "expires_at": expires_at}},
                        upsert=True,
                    )
                    db["hotnews_audio_cache"].delete_many(
                        {"key": re.compile(f"^audio:{re.escape(slug)}")}
                    )
                    return {"slug": slug, **result, "cached": False,
                            "post_count": len(posts), "link_posts": link_posts}

        if not topic_doc:
            raise HTTPException(status_code=404, detail="Hot topic not found")

        keywords = topic_doc.get("keywords", [])
        if not keywords:
            return {"slug": slug, "title": "", "lead": "", "body": [],
                    "conclusion": "", "key_points": [], "sentiment": "neutral",
                    "post_count": 0}

        query = {
            "$and": [
                {"created_at": {"$gte": since}},
                {"$or": [{"text": {"$regex": kw, "$options": "i"}} for kw in keywords]},
            ]
        }
        posts = list(posts_coll.find(query, proj).sort("created_at", -1).limit(30))
        topic_display_name = topic_doc["name"]

    if not posts:
        return {"slug": slug, "title": "", "lead": "", "body": [],
                "conclusion": "", "key_points": [], "sentiment": "neutral",
                "post_count": 0, "link_posts": []}

    result = await cluster_and_summarize(posts, topic_display_name)
    result.pop("_filtered_posts", None)
    link_posts = _extract_link_posts(posts)

    expires_at = datetime.utcnow() + timedelta(minutes=30)
    cache_coll.update_one(
        {"key": cache_key},
        {"$set": {
            "key": cache_key,
            "title": result.get("title", ""),
            "lead": result.get("lead", ""),
            "body": result.get("body", []),
            "conclusion": result.get("conclusion", ""),
            "key_points": result.get("key_points", []),
            "sentiment": result.get("sentiment", "neutral"),
            "ai": result.get("ai", False),
            "post_count": len(posts),
            "link_posts": link_posts,
            "expires_at": expires_at,
        }},
        upsert=True,
    )
    db["hotnews_audio_cache"].delete_many({"key": re.compile(f"^audio:{re.escape(slug)}")})

    return {
        "slug": slug,
        "title": result.get("title", ""),
        "lead": result.get("lead", ""),
        "body": result.get("body", []),
        "conclusion": result.get("conclusion", ""),
        "key_points": result.get("key_points", []),
        "sentiment": result.get("sentiment", "neutral"),
        "ai": result.get("ai", False),
        "cached": False,
        "post_count": len(posts),
        "link_posts": link_posts,
    }


@router.get("/public/hotnews/{slug}/audio")
@limiter.limit("10/minute")
async def get_hotnews_audio(
    request: Request,
    slug: str,
    hours: int = Query(48, ge=1, le=168),
):
    """Trả về file MP3 (TTS) tóm tắt tin nóng. Dùng edge-tts, voice vi-VN-HoaiMyNeural."""
    db = get_db()
    audio_cache = db["hotnews_audio_cache"]
    summary_cache = db["hotnews_summary_cache"]
    now = datetime.utcnow()

    summary_doc = summary_cache.find_one(
        {"key": re.compile(f"^{re.escape(slug)}:\\d+:v2$"), "expires_at": {"$gt": now}},
        sort=[("expires_at", -1)],
    )

    if summary_doc and summary_doc.get("title"):
        summary_bucket = (
            summary_doc["expires_at"].strftime("%Y%m%d%H%M")
            if summary_doc.get("expires_at") else "x"
        )
        cache_key = f"audio:{slug}:{summary_bucket}"

        cached = audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}})
        if cached and cached.get("audio_b64"):
            audio_bytes = base64.b64decode(cached["audio_b64"])
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={"Cache-Control": "public, max-age=7200",
                         "Content-Length": str(len(audio_bytes))},
            )

        parts = []
        for field in ("title", "lead"):
            v = summary_doc.get(field, "")
            if v:
                parts.append(v)
        if summary_doc.get("body"):
            parts.extend(summary_doc["body"])
        if summary_doc.get("conclusion"):
            parts.append(summary_doc["conclusion"])
        if summary_doc.get("key_points"):
            parts.append("Các điểm chính: " + ". ".join(summary_doc["key_points"]))
        tts_text = ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())
    else:
        cache_key = f"audio:{slug}:fallback"
        cached = audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}})
        if cached and cached.get("audio_b64"):
            audio_bytes = base64.b64decode(cached["audio_b64"])
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={"Cache-Control": "public, max-age=7200",
                         "Content-Length": str(len(audio_bytes))},
            )

        cutoff = now - timedelta(hours=max(hours, 6))
        hn_doc = db["hotnews_v2_cache"].find_one(
            {"clusters.slug": slug, "created_at": {"$gte": cutoff}},
            sort=[("created_at", -1)],
        )
        cluster_doc = None
        if hn_doc:
            cluster_doc = next(
                (c for c in (hn_doc.get("clusters") or []) if c.get("slug") == slug),
                None,
            )
        if not cluster_doc:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy dữ liệu cho chủ đề này. Hãy xem tóm tắt AI trước.",
            )
        tts_text = cluster_doc.get("name", slug) + ". " + (cluster_doc.get("headline") or "")

    if len(tts_text) > 7000:
        tts_text = tts_text[:7000]

    try:
        audio_bytes = await _generate_tts_bytes(tts_text)
    except Exception as exc:
        logger.error(f"TTS generation failed for slug={slug}: {exc}")
        raise HTTPException(status_code=503, detail=f"Không thể tạo audio: {exc}")

    if not audio_bytes:
        raise HTTPException(status_code=503, detail="edge-tts trả về dữ liệu trống.")

    expires_at = now + timedelta(hours=2)
    audio_cache.update_one(
        {"key": cache_key},
        {"$set": {
            "key": cache_key,
            "slug": slug,
            "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            "created_at": now,
            "expires_at": expires_at,
        }},
        upsert=True,
    )

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=7200",
                 "Content-Length": str(len(audio_bytes))},
    )
