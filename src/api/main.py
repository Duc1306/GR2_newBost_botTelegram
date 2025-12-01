from __future__ import annotations
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
from src.db.mongo import get_posts_collection
from src.models.post import Post

app = FastAPI(
    title="MXH Aggregator API",
    description="API tổng hợp tin tức từ Telegram",
    version="1.0.0"
)

# CORS middleware để frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Trang chủ API"""
    return {
        "message": "🎉 MXH Aggregator API",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "posts": "/posts",
            "posts_count": "/posts/count",
            "topics": "/topics",
            "stats": "/stats"
        }
    }


@app.get("/health")
async def health():
    """Kiểm tra trạng thái API"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/posts", response_model=List[dict])
async def get_posts(
    source: Optional[str] = Query(None, description="Lọc theo nguồn (telegram, x)"),
    topic: Optional[str] = Query(None, description="Lọc theo chủ đề"),
    lang: Optional[str] = Query(None, description="Lọc theo ngôn ngữ (vi, en)"),
    q: Optional[str] = Query(None, description="Tìm kiếm trong nội dung"),
    link_only: bool = Query(False, description="Chỉ lấy bài có link bên ngoài"),
    topics_only: bool = Query(False, description="Chỉ lấy bài đã phân loại (có ít nhất 1 topic)"),
    limit: int = Query(20, ge=1, le=100, description="Số bài tối đa (1-100)"),
    skip: int = Query(0, ge=0, description="Bỏ qua N bài đầu")
):
    """Lấy danh sách bài viết với filter"""
    coll = get_posts_collection()
    
    # Build query
    query = {}
    if source:
        query["source"] = source
    
    # Topic filter - nếu có topic cụ thể, lọc theo topic đó
    # Nếu không có topic nhưng có topics_only, chỉ lấy bài có topics
    if topic:
        query["topics"] = topic
    elif topics_only:
        query["topics"] = {"$exists": True, "$ne": []}
    
    if lang:
        query["lang"] = lang
    if q:
        query["text"] = {"$regex": q, "$options": "i"}
    if link_only:
        query["links"] = {"$exists": True, "$ne": []}
    
    # Log query for debugging
    print(f"[API] Query: {query}")
    
    # Fetch posts
    cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
    posts = list(cursor)
    
    # Convert ObjectId to string
    for p in posts:
        if "_id" in p:
            p["_id"] = str(p["_id"])
    
    return posts


@app.get("/posts/count")
async def count_posts(
    source: Optional[str] = Query(None, description="Lọc theo nguồn"),
    topic: Optional[str] = Query(None, description="Lọc theo chủ đề"),
    lang: Optional[str] = Query(None, description="Lọc theo ngôn ngữ"),
    link_only: bool = Query(False, description="Chỉ tính bài có link bên ngoài"),
    topics_only: bool = Query(False, description="Chỉ tính bài đã phân loại")
):
    """Đếm số lượng bài viết"""
    coll = get_posts_collection()
    
    query = {}
    if source:
        query["source"] = source
    
    # Topic filter - giống logic trong get_posts
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


@app.get("/topics")
async def get_topics():
    """Lấy danh sách tất cả các chủ đề"""
    coll = get_posts_collection()
    
    # Aggregate unique topics
    pipeline = [
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    topics = list(coll.aggregate(pipeline))
    result = [{"topic": t["_id"], "count": t["count"]} for t in topics]
    
    return {"topics": result, "total": len(result)}


@app.get("/stats")
async def get_stats(
    link_only: bool = Query(False, description="Chỉ thống kê bài có link"),
    topics_only: bool = Query(False, description="Chỉ bài có ít nhất 1 topic"),
    lang: Optional[str] = Query(None, description="Giới hạn theo ngôn ngữ cụ thể (vi/en)")
):
    """Thống kê tổng quan (có thể lọc theo link/topic/ngôn ngữ)."""
    coll = get_posts_collection()

    base_query: dict = {}
    if link_only:
        base_query["links"] = {"$exists": True, "$ne": []}
    if topics_only:
        # Đảm bảo có ít nhất 1 phần tử trong topics
        base_query["topics"] = {"$exists": True, "$ne": []}
    if lang:
        base_query["lang"] = lang

    total_filtered = coll.count_documents(base_query)

    # Count by source (theo filter)
    sources_pipeline = [
        {"$match": base_query},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    sources = list(coll.aggregate(sources_pipeline))

    # Count by language (theo filter)
    languages_pipeline = [
        {"$match": base_query},
        {"$group": {"_id": "$lang", "count": {"$sum": 1}}}
    ]
    languages = list(coll.aggregate(languages_pipeline))

    # Count by topic (theo filter)
    topics_pipeline = [
        {"$match": {**base_query, "topics": {"$exists": True, "$ne": []}}},
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    topics = list(coll.aggregate(topics_pipeline))

    # Latest post theo filter
    latest = coll.find_one(base_query, sort=[("created_at", -1)])
    latest_date = latest["created_at"] if latest else None

    return {
        "total_posts": total_filtered,
        "filter": base_query,
        "by_source": {s["_id"]: s["count"] for s in sources if s["_id"] is not None},
        "by_language": {l["_id"]: l["count"] for l in languages if l["_id"] is not None},
        "by_topic": {t["_id"]: t["count"] for t in topics if t["_id"] is not None},
        "latest_post_date": latest_date
    }


@app.get("/posts/{post_id}")
async def get_post_by_id(post_id: str):
    """Lấy chi tiết một bài viết"""
    coll = get_posts_collection()
    
    post = coll.find_one({"id": post_id})
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if "_id" in post:
        post["_id"] = str(post["_id"])
    
    return post
