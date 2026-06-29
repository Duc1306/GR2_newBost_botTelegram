"""Admin routes: ML metrics, X fetch, hot topics management, AI tools, user management."""
from __future__ import annotations
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from src.db.mongo import get_db, get_users_collection
from src.api.auth import get_current_admin_user
from src.models.user import UpdateUserStatusRequest, UpdateUserRoleRequest
from src.api.routes.hotnews_routes import (
    DEFAULT_HOT_TOPICS,
    clear_hotnews_caches,
    rebuild_hotnews_after_fetch,
)

router = APIRouter(tags=["Admin"])


def _clean_slug(slug: str) -> str:
    return (slug or "").strip()


def _slug_lookup(slug: str) -> dict:
    clean = _clean_slug(slug)
    return {
        "$or": [
            {"slug": clean},
            {"$expr": {"$eq": [{"$trim": {"input": "$slug"}}, clean]}},
        ]
    }


# =============================================================================
# ML Model Metrics
# =============================================================================

@router.get("/admin/ml-metrics")
async def get_ml_metrics(current_user: str = Depends(get_current_admin_user)):
    """Trả về báo cáo đánh giá mô hình ML từ file evaluation_report.json."""
    import json as _json

    report_path = Path("models") / "evaluation_report.json"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Chưa có báo cáo đánh giá. Hãy chạy scripts/evaluate_model.py trước.",
        )
    try:
        with open(report_path, encoding="utf-8") as f:
            report = _json.load(f)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể đọc file báo cáo: {exc}")


# =============================================================================
# X (Twitter) Scrape on-demand
# =============================================================================

class XFetchRequest(BaseModel):
    keywords: List[str]
    max_items: int = 50
    language: str = "vi"


@router.post("/admin/x/fetch", tags=["Admin"])
async def admin_fetch_x(
    body: XFetchRequest,
    current_user: str = Depends(get_current_admin_user),
):
    """Kích hoạt cào tweet theo từ khóa ngay lập tức (Apify Actor)."""
    from src.config import APIFY_API_TOKEN as _APIFY_TOKEN

    if not _APIFY_TOKEN:
        raise HTTPException(status_code=503, detail="APIFY_API_TOKEN chưa được cấu hình trong .env")
    if not body.keywords:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 từ khóa")

    try:
        from src.ingestion.x_worker import ingest_once
        saved = await ingest_once(
            mode="keyword",
            keywords=body.keywords,
            max_items=body.max_items,
            language=body.language,
        )
        if saved > 0:
            await rebuild_hotnews_after_fetch(get_db(), reason="admin X fetch")
        return {"saved": saved, "keywords": body.keywords}
    except Exception as exc:
        logger.error(f"[admin/x/fetch] error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# =============================================================================
# Hotnews Cache Management
# =============================================================================

@router.delete("/admin/hotnews-cache")
async def clear_hotnews_cache(current_user: str = Depends(get_current_admin_user)):
    """Force-clear all hotnews caches so the next request recomputes fresh."""
    deleted = clear_hotnews_caches(get_db())
    return {
        "deleted_filter": deleted.get("hotnews_filter_cache", 0),
        "deleted_clusters": deleted.get("hotnews_v2_cache", 0),
        "deleted_summaries": deleted.get("hotnews_summary_cache", 0),
        "deleted_audio": deleted.get("hotnews_audio_cache", 0),
        "message": "All hotnews caches cleared. Next request will recompute.",
    }


@router.delete("/admin/hotnews-audio-cache/{slug}")
async def clear_audio_cache_for_slug(
    slug: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Xóa audio cache của một slug cụ thể."""
    db = get_db()
    r = db["hotnews_audio_cache"].delete_many({"key": re.compile(f"^audio:{re.escape(slug)}")})
    return {
        "deleted": r.deleted_count,
        "slug": slug,
        "message": f"Đã xóa {r.deleted_count} audio cache entries cho '{slug}'.",
    }


# =============================================================================
# Hot Topics Management
# =============================================================================

@router.post("/admin/hot-topics/seed")
async def seed_hot_topics(current_user: str = Depends(get_current_admin_user)):
    """Seed default hot topics into the database (idempotent)."""
    db = get_db()
    coll = db["hot_topics"]

    seeded = 0
    already_existed = 0
    for topic in DEFAULT_HOT_TOPICS:
        doc = {**topic, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
        result = coll.update_one(
            {"slug": topic["slug"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        if result.upserted_id:
            seeded += 1
        else:
            already_existed += 1

    return {"seeded": seeded, "already_existed": already_existed, "total": len(DEFAULT_HOT_TOPICS)}


@router.get("/admin/hot-topics")
async def admin_list_hot_topics(current_user: str = Depends(get_current_admin_user)):
    """Admin: list all hot topics (including inactive)."""
    db = get_db()
    topics = list(db["hot_topics"].find({}, {"_id": 0}).sort("priority", 1))
    return {"topics": topics}


@router.post("/admin/hot-topics")
async def admin_create_hot_topic(
    topic: dict,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: create a new hot topic."""
    db = get_db()
    coll = db["hot_topics"]

    for field in ("slug", "name", "keywords"):
        if field not in topic:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    slug = _clean_slug(topic["slug"])
    if not slug:
        raise HTTPException(status_code=400, detail="Slug cannot be empty")

    if coll.find_one(_slug_lookup(slug)):
        raise HTTPException(status_code=409, detail="Slug already exists")

    doc = {
        "slug": slug,
        "name": str(topic["name"]).strip(),
        "description": topic.get("description", ""),
        "keywords": topic["keywords"],
        "color": topic.get("color", "#6b7280"),
        "priority": topic.get("priority", 99),
        "active": topic.get("active", True),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    coll.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "topic": doc}


@router.put("/admin/hot-topics/{slug}")
async def admin_update_hot_topic(
    slug: str,
    updates: dict,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: update an existing hot topic."""
    db = get_db()
    coll = db["hot_topics"]

    for field in ("slug", "_id", "created_at"):
        updates.pop(field, None)
    updates["updated_at"] = datetime.utcnow()

    clean_slug = _clean_slug(slug)
    updates["slug"] = clean_slug
    result = coll.update_one(_slug_lookup(clean_slug), {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hot topic not found")
    return {"success": True}


@router.delete("/admin/hot-topics/{slug}")
async def admin_delete_hot_topic(
    slug: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: delete a hot topic."""
    db = get_db()
    result = db["hot_topics"].delete_one(_slug_lookup(slug))
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hot topic not found")
    return {"success": True}


# =============================================================================
# AI-powered Hot Topics
# =============================================================================

@router.get("/admin/ai/status", tags=["AI"])
async def ai_status(current_user: str = Depends(get_current_admin_user)):
    """Check whether OpenAI is configured and reachable."""
    from src.processing.ai_topic_detector import check_openai_status
    return await check_openai_status()


@router.post("/admin/ai/detect-hot-topics", tags=["AI"])
async def ai_detect_hot_topics(
    hours: int = Query(24, ge=1, le=168),
    max_topics: int = Query(5, ge=1, le=10),
    auto_save: bool = Query(False),
    current_user: str = Depends(get_current_admin_user),
):
    """Use GPT-4o-mini to analyse recent posts and suggest NEW hot topics."""
    from src.processing.ai_topic_detector import detect_new_hot_topics
    db = get_db()

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cursor = db["posts"].find(
        {"created_at": {"$gte": cutoff}},
        {"text": 1, "_id": 0},
    ).sort("created_at", -1).limit(80)
    posts = list(cursor)

    if not posts:
        return {"suggestions": [], "message": "No posts found in the given time window"}

    existing_slugs = [t["slug"] for t in db["hot_topics"].find({}, {"slug": 1, "_id": 0})]
    suggestions = await detect_new_hot_topics(
        posts, existing_slugs=existing_slugs, max_new_topics=max_topics,
    )

    if auto_save and suggestions:
        now = datetime.utcnow()
        for topic in suggestions:
            doc = {**topic, "created_at": now, "updated_at": now}
            db["hot_topics"].update_one(
                {"slug": topic["slug"]},
                {"$setOnInsert": doc},
                upsert=True,
            )

    return {
        "suggestions": suggestions,
        "posts_analysed": len(posts),
        "hours_window": hours,
        "auto_saved": auto_save,
    }


@router.post("/admin/ai/expand-keywords/{slug}", tags=["AI"])
async def ai_expand_keywords(
    slug: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Use GPT-4o-mini to expand the keyword list for an existing hot topic."""
    from src.processing.ai_topic_detector import expand_keywords
    db = get_db()
    coll = db["hot_topics"]
    clean_slug = _clean_slug(slug)

    topic = coll.find_one(_slug_lookup(clean_slug), {"_id": 0})
    if not topic:
        topic = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == clean_slug), None)
        if not topic:
            raise HTTPException(status_code=404, detail="Hot topic not found")

    original_keywords = topic.get("keywords", [])
    expanded = await expand_keywords(topic["name"], original_keywords)
    new_count = len(expanded) - len(original_keywords)

    coll.update_one(
        _slug_lookup(clean_slug),
        {"$set": {"slug": clean_slug, "keywords": expanded, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

    return {
        "slug": clean_slug,
        "original_count": len(original_keywords),
        "expanded_count": len(expanded),
        "new_keywords_added": new_count,
        "keywords": expanded,
    }


# =============================================================================
# User Management
# =============================================================================

@router.get("/admin/users", tags=["Admin - Users"])
async def admin_list_users(
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Danh sách tất cả user có bộ lọc."""
    users_col = get_users_collection()
    query: dict = {}
    if status:
        query["status"] = status
    if role:
        query["role"] = role
    if q:
        query["$or"] = [
            {"username": {"$regex": re.escape(q), "$options": "i"}},
            {"email": {"$regex": re.escape(q), "$options": "i"}},
            {"full_name": {"$regex": re.escape(q), "$options": "i"}},
        ]

    total = users_col.count_documents(query)
    docs = list(
        users_col.find(query, {"password_hash": 0, "_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return {"users": docs, "total": total, "skip": skip, "limit": limit}


@router.get("/admin/users/stats/summary", tags=["Admin - Users"])
async def admin_users_stats(current_user: str = Depends(get_current_admin_user)):
    """Admin: Thống kê user theo trạng thái & vai trò."""
    users_col = get_users_collection()
    pipeline = [
        {"$group": {
            "_id": {"status": "$status", "role": "$role"},
            "count": {"$sum": 1},
        }}
    ]
    rows = list(users_col.aggregate(pipeline))
    total = users_col.count_documents({})
    by_status: dict = {}
    by_role: dict = {}
    for r in rows:
        s = r["_id"]["status"]
        rl = r["_id"]["role"]
        by_status[s] = by_status.get(s, 0) + r["count"]
        by_role[rl] = by_role.get(rl, 0) + r["count"]
    return {"total": total, "by_status": by_status, "by_role": by_role}


@router.get("/admin/users/{username}", tags=["Admin - Users"])
async def admin_get_user(
    username: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Xem chi tiết một user."""
    users_col = get_users_collection()
    doc = users_col.find_one({"username": username}, {"password_hash": 0, "_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc


@router.put("/admin/users/{username}/status", tags=["Admin - Users"])
async def admin_update_user_status(
    username: str,
    body: UpdateUserStatusRequest,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Thay đổi trạng thái tài khoản (active / banned / pending)."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản của mình.")
    users_col = get_users_collection()
    result = users_col.update_one({"username": username}, {"$set": {"status": body.status}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Admin {current_user} changed {username} status → {body.status}")
    return {"success": True, "username": username, "status": body.status}


@router.put("/admin/users/{username}/role", tags=["Admin - Users"])
async def admin_update_user_role(
    username: str,
    body: UpdateUserRoleRequest,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Thay đổi vai trò (user / admin)."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Không thể tự đổi vai trò của mình.")
    users_col = get_users_collection()
    result = users_col.update_one({"username": username}, {"$set": {"role": body.role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Admin {current_user} changed {username} role → {body.role}")
    return {"success": True, "username": username, "role": body.role}


@router.delete("/admin/users/{username}", tags=["Admin - Users"])
async def admin_delete_user(
    username: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Xóa tài khoản user và toàn bộ dữ liệu liên quan."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Không thể tự xóa tài khoản của mình.")
    users_col = get_users_collection()

    user_doc = users_col.find_one({"username": username}, {"_id": 1})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_id_str = str(user_doc["_id"])
    db = get_db()

    users_col.delete_one({"_id": user_doc["_id"]})
    db["user_channels"].delete_many({"user_id": user_id_str})
    db["notifications"].delete_many({"user": username})
    db["user_settings"].delete_many({"username": username})

    logger.info(f"Admin {current_user} deleted user {username} (id={user_id_str}) + related data")
    return {"success": True}


# =============================================================================
# Backfill: topics + geo classification
# =============================================================================

class BackfillRequest(BaseModel):
    limit: int = 5000
    geo_only: bool = False
    ai_only: bool = False
    count_only: bool = False   # chỉ đếm, không xử lý


@router.post("/admin/backfill/topics-geo", tags=["Admin"])
async def admin_backfill_topics_geo(
    body: BackfillRequest,
    current_user: str = Depends(get_current_admin_user),
):
    """Kích hoạt backfill topics (rule-based + OpenAI fallback) và geo cho bài viết còn thiếu.

    - `count_only=true`: chỉ đếm số bài thiếu + ước tính chi phí, không xử lý.
    - `geo_only=true`: chỉ backfill geo, bỏ qua topic.
    - `ai_only=true`: dùng OpenAI cho tất cả (không chạy rule-based trước).
    - `limit`: số bài xử lý tối đa mỗi lần (mặc định 5000).
    """
    from src.processing.backfill_topics import backfill_async, count_missing

    if body.count_only:
        result = count_missing(verbose=False)
        est_topic = result["missing_topics"] * 150 / 1_000_000 * 0.15
        est_geo   = result["missing_geo"]    * 100 / 1_000_000 * 0.15
        return {
            **result,
            "est_topic_cost_usd": round(est_topic, 4),
            "est_geo_cost_usd":   round(est_geo,   4),
        }

    logger.info(
        f"[admin/backfill] {current_user} triggered backfill "
        f"limit={body.limit} geo_only={body.geo_only} ai_only={body.ai_only}"
    )
    try:
        stats = await backfill_async(
            limit=body.limit,
            geo_only=body.geo_only,
            ai_only=body.ai_only,
        )
        return {"success": True, **stats}
    except Exception as exc:
        logger.error(f"[admin/backfill] error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
