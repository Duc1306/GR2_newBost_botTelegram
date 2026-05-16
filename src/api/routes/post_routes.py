"""Post, topic, stats, and user bookmark routes."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from pydantic import BaseModel
from loguru import logger

from src.db.mongo import get_db
from src.api.auth import get_current_user
from src.api.middleware import limiter

router = APIRouter()


# =============================================================================
# Post Endpoints
# =============================================================================

@router.get("/posts", response_model=List[dict], tags=["Posts"])
@limiter.limit("100/minute")
async def get_posts(
    request: Request,
    platform: Optional[str] = Query("all", description="Filter by platform (telegram, twitter, all)"),
    source: Optional[str] = Query(None, description="Lọc theo nguồn (telegram, x)"),
    topic: Optional[str] = Query(None, description="Lọc theo chủ đề"),
    lang: Optional[str] = Query(None, description="Lọc theo ngôn ngữ (vi, en)"),
    q: Optional[str] = Query(None, description="Tìm kiếm trong nội dung"),
    link_only: bool = Query(False, description="Chỉ lấy bài có link bên ngoài"),
    topics_only: bool = Query(False, description="Chỉ lấy bài đã phân loại (có ít nhất 1 topic)"),
    limit: int = Query(20, ge=1, le=100, description="Số bài tối đa (1-100)"),
    skip: int = Query(0, ge=0, description="Bỏ qua N bài đầu"),
    current_user: str = Depends(get_current_user),
):
    """Lấy danh sách bài viết với filter."""
    db = get_db()
    coll = db["posts"]

    query: dict = {}
    if platform and platform != "all":
        query["platform"] = platform
    if source:
        query["source"] = source
    if topic:
        query["topics"] = topic
    elif topics_only:
        query["topics"] = {"$exists": True, "$ne": []}
    if lang:
        query["lang"] = lang
    if q:
        query["$text"] = {"$search": q}
    if link_only:
        query["links"] = {"$exists": True, "$ne": []}

    cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
    posts = list(cursor)
    for p in posts:
        if "_id" in p:
            p["_id"] = str(p["_id"])
    return posts


@router.get("/posts/count", tags=["Posts"])
async def count_posts(
    source: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    lang: Optional[str] = Query(None),
    link_only: bool = Query(False),
    topics_only: bool = Query(False),
    platform: Optional[str] = Query("all"),
    current_user: str = Depends(get_current_user),
):
    """Đếm số lượng bài viết."""
    db = get_db()
    coll = db["posts"]

    query: dict = {}
    if platform and platform != "all":
        query["platform"] = platform
    if source:
        query["source"] = source
    if topic:
        query["topics"] = topic
    elif topics_only:
        query["topics"] = {"$exists": True, "$ne": []}
    if lang:
        query["lang"] = lang
    if link_only:
        query["links"] = {"$exists": True, "$ne": []}

    count = coll.count_documents(query)
    return {"count": count, "filter": query}


@router.get("/topics", tags=["Posts"])
async def get_topics(
    platform: Optional[str] = Query("all"),
    current_user: str = Depends(get_current_user),
):
    """Lấy danh sách tất cả các chủ đề."""
    db = get_db()
    coll = db["posts"]

    match_query: dict = {}
    if platform and platform != "all":
        match_query["platform"] = platform

    pipeline = []
    if match_query:
        pipeline.append({"$match": match_query})
    pipeline.extend([
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ])

    topics = list(coll.aggregate(pipeline))
    result = [{"topic": t["_id"], "count": t["count"]} for t in topics]
    return {"topics": result, "total": len(result)}


@router.get("/stats", tags=["Posts"])
async def get_stats(
    link_only: bool = Query(False),
    topics_only: bool = Query(False),
    lang: Optional[str] = Query(None),
    platform: Optional[str] = Query("all"),
    current_user: str = Depends(get_current_user),
):
    """Thống kê tổng quan."""
    db = get_db()
    coll = db["posts"]

    base_query: dict = {}
    if platform and platform != "all":
        base_query["platform"] = platform
    if link_only:
        base_query["links"] = {"$exists": True, "$ne": []}
    if topics_only:
        base_query["topics"] = {"$exists": True, "$ne": []}
    if lang:
        base_query["lang"] = lang

    facet_result = list(coll.aggregate([
        {"$match": base_query},
        {"$facet": {
            "total": [{"$count": "n"}],
            "sources": [{"$group": {"_id": "$source", "count": {"$sum": 1}}}],
            "languages": [{"$group": {"_id": "$lang", "count": {"$sum": 1}}}],
            "topics": [
                {"$match": {"topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ],
            "platforms": [{"$group": {"_id": "$platform", "count": {"$sum": 1}}}],
            "labeled_count": [
                {"$match": {"topics": {"$exists": True, "$ne": []}}},
                {"$count": "count"},
            ],
            "latest": [
                {"$sort": {"created_at": -1}},
                {"$limit": 1},
                {"$project": {"created_at": 1}},
            ],
        }},
    ]))

    facet = facet_result[0] if facet_result else {}
    total_filtered = (facet.get("total", [{}])[0] or {}).get("n", 0)
    sources = facet.get("sources", [])
    languages = facet.get("languages", [])
    topics = facet.get("topics", [])
    platforms = facet.get("platforms", [])
    labeled_posts_count = (facet.get("labeled_count", [{}])[0] or {}).get("count", 0)
    latest_doc = (facet.get("latest") or [None])[0]
    latest_date = latest_doc["created_at"] if latest_doc else None

    _PLATFORM_MAP = {"twitter": "x", "x": "x", "telegram": "telegram"}
    by_platform: dict = {"telegram": 0, "x": 0}
    for p in platforms:
        raw_key = (p["_id"] or "telegram").lower()
        key = _PLATFORM_MAP.get(raw_key, raw_key)
        by_platform[key] = by_platform.get(key, 0) + p["count"]

    channels_coll = db["channels"]
    channel_meta_coll = db["channel_metadata"]
    active_channels_telegram = channel_meta_coll.count_documents({"platform": "telegram"})
    active_channels_x = channels_coll.count_documents(
        {"status": "active", "platform": {"$in": ["x", "twitter"]}}
    )

    return {
        "total_posts": total_filtered,
        "labeled_posts": labeled_posts_count,
        "filter": base_query,
        "by_source": {s["_id"]: s["count"] for s in sources if s["_id"] is not None},
        "by_language": {l["_id"]: l["count"] for l in languages if l["_id"] is not None},
        "by_topic": {t["_id"]: t["count"] for t in topics if t["_id"] is not None},
        "by_platform": by_platform,
        "active_channels": {
            "total": active_channels_telegram + active_channels_x,
            "telegram": active_channels_telegram,
            "x": active_channels_x,
        },
        "latest_post_date": latest_date,
    }


@router.get("/posts/{post_id}", tags=["Posts"])
async def get_post_by_id(post_id: str, current_user: str = Depends(get_current_user)):
    """Lấy chi tiết một bài viết."""
    db = get_db()
    coll = db["posts"]

    post = coll.find_one({"id": post_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if "_id" in post:
        post["_id"] = str(post["_id"])
    return post


# =============================================================================
# User Bookmark Endpoints
# =============================================================================

class BookmarkRequest(BaseModel):
    post_id: str


@router.post("/user/bookmarks", tags=["User"])
async def add_bookmark(
    body: BookmarkRequest,
    current_user: str = Depends(get_current_user),
):
    """Lưu bài viết vào danh sách bookmark của user."""
    db = get_db()
    db["bookmarks"].update_one(
        {"username": current_user, "post_id": body.post_id},
        {"$set": {
            "username": current_user,
            "post_id": body.post_id,
            "created_at": datetime.utcnow(),
        }},
        upsert=True,
    )
    return {"success": True, "post_id": body.post_id}


@router.get("/user/bookmarks", tags=["User"])
async def get_bookmarks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: str = Depends(get_current_user),
):
    """Lấy danh sách bài viết đã lưu của user."""
    db = get_db()
    bookmarks_coll = db["bookmarks"]
    posts_coll = db["posts"]

    bookmark_docs = list(
        bookmarks_coll.find({"username": current_user})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    total = bookmarks_coll.count_documents({"username": current_user})
    post_ids = [b["post_id"] for b in bookmark_docs]

    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1, "media": 1,
    }
    posts = []
    for pid in post_ids:
        p = posts_coll.find_one({"id": pid}, projection)
        if p:
            p["_id"] = str(p["_id"])
            posts.append(p)

    return {"posts": posts, "total": total, "post_ids": post_ids}


@router.delete("/user/bookmarks/{post_id}", tags=["User"])
async def remove_bookmark(
    post_id: str,
    current_user: str = Depends(get_current_user),
):
    """Xoá bookmark."""
    db = get_db()
    db["bookmarks"].delete_one({"username": current_user, "post_id": post_id})
    return {"success": True, "post_id": post_id}


@router.get("/user/bookmarks/ids", tags=["User"])
async def get_bookmark_ids(current_user: str = Depends(get_current_user)):
    """Trả về danh sách post_id đã bookmark."""
    db = get_db()
    ids = [b["post_id"] for b in db["bookmarks"].find({"username": current_user}, {"post_id": 1})]
    return {"post_ids": ids}
