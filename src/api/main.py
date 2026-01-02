from __future__ import annotations
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
from src.db.mongo import get_db
from src.models.post import Post

app = FastAPI(
    title="MXH Aggregator API",
    description="API tổng hợp tin tức từ Telegram & Twitter với ML Analytics",
    version="2.0.0"
)

# CORS middleware để frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Trang chủ API"""
    return {
        "message": "🎉 MXH Aggregator API v2.0",
        "docs": "/docs",
        "endpoints": {
            "core": {
                "health": "/health",
                "posts": "/posts",
                "posts_count": "/posts/count",
                "topics": "/topics",
                "stats": "/stats"
            },
            "analytics": {
                "trends": "/analytics/trends",
                "keywords": "/analytics/keywords",
                "keywords_trending": "/analytics/keywords/trending",
                "comparison": "/analytics/comparison",
                "timeline": "/analytics/timeline"
            },
            "topics": {
                "list": "/topics",
                "trending": "/topics/trending",
                "stats": "/topics/stats"
            }
        }
    }


@app.get("/health")
async def health():
    """Kiểm tra trạng thái API"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/posts", response_model=List[dict])
async def get_posts(
    platform: Optional[str] = Query("all", description="Filter by platform (telegram, twitter, all)"),
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
    db = get_db()
    coll = db["posts"]
    
    # Build query
    query = {}
    if platform and platform != "all":
        query["platform"] = platform
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
    topics_only: bool = Query(False, description="Chỉ tính bài đã phân loại"),
    platform: Optional[str] = Query("all", description="Filter by platform")
):
    """Đếm số lượng bài viết"""
    db = get_db()
    coll = db["posts"]
    
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
async def get_topics(
    platform: Optional[str] = Query("all", description="Filter by platform")
):
    """Lấy danh sách tất cả các chủ đề"""
    db = get_db()
    coll = db["posts"]
    
    # Build query
    match_query = {}
    if platform and platform != "all":
        match_query["platform"] = platform
    
    # Aggregate unique topics
    pipeline = []
    if match_query:
        pipeline.append({"$match": match_query})
    
    pipeline.extend([
        {"$unwind": "$topics"},
        {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    
    topics = list(coll.aggregate(pipeline))
    result = [{"topic": t["_id"], "count": t["count"]} for t in topics]
    
    return {"topics": result, "total": len(result)}


@app.get("/stats")
async def get_stats(
    link_only: bool = Query(False, description="Chỉ thống kê bài có link"),
    topics_only: bool = Query(False, description="Chỉ bài có ít nhất 1 topic"),
    lang: Optional[str] = Query(None, description="Giới hạn theo ngôn ngữ cụ thể (vi/en)"),
    platform: Optional[str] = Query("all", description="Filter by platform")
):
    """Thống kê tổng quan (có thể lọc theo link/topic/ngôn ngữ)."""
    db = get_db()
    coll = db["posts"]

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
    db = get_db()
    coll = db["posts"]
    
    post = coll.find_one({"id": post_id})
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if "_id" in post:
        post["_id"] = str(post["_id"])
    
    return post


# ============================================================
# ANALYTICS ENDPOINTS
# ============================================================

@app.get("/topics/trending")
async def get_trending_topics(
    days: int = Query(7, ge=1, le=90, description="Time window in days"),
    platform: Optional[str] = Query("all", description="Filter by platform"),
    limit: int = Query(10, ge=1, le=50, description="Top N trending topics")
):
    """Get trending topics (rising in popularity)"""
    db = get_db()
    topic_stats = db["topic_stats"]
    
    # Calculate date range
    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    mid_date = end_date - timedelta(days=days//2)
    
    # Get recent stats
    recent_stats = list(topic_stats.find({
        "date": {"$gte": mid_date, "$lt": end_date},
        "platform": platform
    }))
    
    # Get previous stats
    previous_stats = list(topic_stats.find({
        "date": {"$gte": start_date, "$lt": mid_date},
        "platform": platform
    }))
    
    # Aggregate by topic
    recent_by_topic = {}
    for stat in recent_stats:
        topic = stat["topic"]
        if topic not in recent_by_topic:
            recent_by_topic[topic] = {"count": 0, "confidence": []}
        recent_by_topic[topic]["count"] += stat["post_count"]
        recent_by_topic[topic]["confidence"].append(stat.get("avg_confidence", 0))
    
    previous_by_topic = {}
    for stat in previous_stats:
        topic = stat["topic"]
        if topic not in previous_by_topic:
            previous_by_topic[topic] = {"count": 0}
        previous_by_topic[topic]["count"] += stat["post_count"]
    
    # Calculate trends
    trends = []
    for topic, data in recent_by_topic.items():
        current_count = data["count"]
        previous_count = previous_by_topic.get(topic, {}).get("count", 1)
        
        growth_rate = (current_count - previous_count) / previous_count if previous_count > 0 else 0
        trend_score = current_count / previous_count if previous_count > 0 else 1.0
        
        if trend_score > 1.2:
            trend_direction = "up"
        elif trend_score < 0.8:
            trend_direction = "down"
        else:
            trend_direction = "stable"
        
        avg_confidence = sum(data["confidence"]) / len(data["confidence"]) if data["confidence"] else 0
        
        trends.append({
            "topic": topic,
            "current_count": current_count,
            "previous_count": previous_count,
            "growth_rate": round(growth_rate, 2),
            "trend_direction": trend_direction,
            "trend_score": round(trend_score, 2),
            "avg_confidence": round(avg_confidence, 3)
        })
    
    # Sort by trend_score and limit
    trends.sort(key=lambda x: x["trend_score"], reverse=True)
    trends = trends[:limit]
    
    return {
        "data": trends,
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "days": days
        }
    }


@app.get("/analytics/keywords")
async def get_keywords(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=200, description="Top N keywords"),
    min_count: int = Query(5, ge=1, description="Minimum frequency")
):
    """Get top keywords by frequency"""
    db = get_db()
    keyword_trends = db["keyword_trends"]
    
    # Parse dates
    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Build query
    query = {
        "date": {"$gte": start_date, "$lte": end_date},
        "total_count": {"$gte": min_count}
    }
    
    # Fetch keywords
    cursor = keyword_trends.find(query).sort("total_count", -1).limit(limit * 2)
    keywords_data = list(cursor)
    
    # Aggregate by keyword (sum across dates)
    keywords_agg = {}
    for kw_doc in keywords_data:
        kw = kw_doc["keyword"]
        if kw not in keywords_agg:
            keywords_agg[kw] = {
                "count": 0,
                "unique_posts": 0,
                "platforms": {"telegram": 0, "twitter": 0},
                "topics": {},
                "trend_velocities": []
            }
        
        keywords_agg[kw]["count"] += kw_doc.get("total_count", 0)
        keywords_agg[kw]["unique_posts"] += kw_doc.get("unique_posts", 0)
        
        # Platforms
        platforms_data = kw_doc.get("platforms", {})
        keywords_agg[kw]["platforms"]["telegram"] += platforms_data.get("telegram", 0)
        keywords_agg[kw]["platforms"]["twitter"] += platforms_data.get("twitter", 0)
        
        # Topics
        topics_data = kw_doc.get("topics", {})
        for t, cnt in topics_data.items():
            if topic is None or t == topic:
                keywords_agg[kw]["topics"][t] = keywords_agg[kw]["topics"].get(t, 0) + cnt
        
        # Trend velocity
        if "trend_velocity" in kw_doc:
            keywords_agg[kw]["trend_velocities"].append(kw_doc["trend_velocity"])
    
    # Filter by topic if specified
    if topic:
        keywords_agg = {
            k: v for k, v in keywords_agg.items()
            if topic in v["topics"]
        }
    
    # Format result
    keywords_result = []
    for kw, data in keywords_agg.items():
        avg_velocity = sum(data["trend_velocities"]) / len(data["trend_velocities"]) if data["trend_velocities"] else 1.0
        
        keywords_result.append({
            "keyword": kw,
            "count": data["count"],
            "unique_posts": data["unique_posts"],
            "platforms": data["platforms"],
            "topics": data["topics"],
            "trend_velocity": round(avg_velocity, 2)
        })
    
    # Sort and limit
    keywords_result.sort(key=lambda x: x["count"], reverse=True)
    keywords_result = keywords_result[:limit]
    
    return {
        "keywords": keywords_result,
        "total": len(keywords_result),
        "period": {
            "from": date_from,
            "to": date_to
        }
    }


@app.get("/analytics/keywords/trending")
async def get_trending_keywords(
    days: int = Query(7, ge=1, le=30, description="Time window"),
    limit: int = Query(20, ge=1, le=100, description="Top N keywords"),
    min_velocity: float = Query(1.5, ge=1.0, description="Minimum trend velocity")
):
    """Get trending keywords (fastest growing)"""
    db = get_db()
    keyword_trends = db["keyword_trends"]
    
    # Calculate date range
    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    
    # Get recent keywords with high velocity
    cursor = keyword_trends.find({
        "date": {"$gte": start_date, "$lt": end_date},
        "trend_velocity": {"$gte": min_velocity}
    }).sort("trend_velocity", -1)
    
    keywords_data = list(cursor)
    
    # Aggregate by keyword
    keywords_agg = {}
    for kw_doc in keywords_data:
        kw = kw_doc["keyword"]
        if kw not in keywords_agg:
            keywords_agg[kw] = {
                "total_count": 0,
                "velocities": [],
                "topics": set()
            }
        
        keywords_agg[kw]["total_count"] += kw_doc.get("total_count", 0)
        keywords_agg[kw]["velocities"].append(kw_doc.get("trend_velocity", 1.0))
        
        # Topics
        for topic in kw_doc.get("topics", {}).keys():
            keywords_agg[kw]["topics"].add(topic)
    
    # Format result
    trending_keywords = []
    for kw, data in keywords_agg.items():
        avg_velocity = sum(data["velocities"]) / len(data["velocities"])
        max_velocity = max(data["velocities"])
        
        trending_keywords.append({
            "keyword": kw,
            "current_count": data["total_count"],
            "trend_velocity": round(avg_velocity, 2),
            "max_velocity": round(max_velocity, 2),
            "trend_direction": "up",
            "related_topics": list(data["topics"])
        })
    
    # Sort and limit
    trending_keywords.sort(key=lambda x: x["trend_velocity"], reverse=True)
    trending_keywords = trending_keywords[:limit]
    
    return {
        "keywords": trending_keywords,
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "days": days
        }
    }


@app.get("/analytics/timeline")
async def get_timeline(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    granularity: str = Query("day", regex="^(day|week)$", description="Time granularity")
):
    """Get post volume timeline"""
    db = get_db()
    posts = db["posts"]
    
    # Parse dates
    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Build query
    query = {
        "created_at": {"$gte": start_date, "$lte": end_date}
    }
    
    if platform and platform != "all":
        query["platform"] = platform
    
    if topic:
        query["topic_predictions.topic"] = topic
    
    # Aggregation pipeline
    if granularity == "day":
        date_format = "%Y-%m-%d"
        group_id = {
            "$dateToString": {"format": date_format, "date": "$created_at"}
        }
    else:  # week
        date_format = "%Y-W%V"
        group_id = {
            "$dateToString": {"format": date_format, "date": "$created_at"}
        }
    
    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": group_id,
                "count": {"$sum": 1},
                "platforms": {"$push": "$platform"},
                "topics": {"$push": "$topics"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = list(posts.aggregate(pipeline))
    
    # Format timeline
    timeline = []
    total_posts = 0
    max_count = 0
    peak_date = None
    
    for result in results:
        count = result["count"]
        total_posts += count
        
        if count > max_count:
            max_count = count
            peak_date = result["_id"]
        
        # Count by platform
        platforms_count = {}
        for p in result["platforms"]:
            platforms_count[p] = platforms_count.get(p, 0) + 1
        
        # Count by topic (flatten)
        topics_count = {}
        for topics_list in result["topics"]:
            for t in topics_list:
                topics_count[t] = topics_count.get(t, 0) + 1
        
        timeline.append({
            "date": result["_id"],
            "count": count,
            "by_platform": platforms_count,
            "by_topic": topics_count
        })
    
    avg_per_period = total_posts / len(timeline) if timeline else 0
    
    return {
        "timeline": timeline,
        "summary": {
            "total_posts": total_posts,
            "avg_per_period": round(avg_per_period, 1),
            "peak_date": peak_date,
            "peak_count": max_count
        },
        "period": {
            "from": date_from,
            "to": date_to
        }
    }


@app.get("/analytics/comparison")
async def get_platform_comparison(
    date_from: str = Query(..., description="Start date"),
    date_to: str = Query(..., description="End date"),
    metric: str = Query("volume", regex="^(volume|topics|keywords)$")
):
    """Compare platforms (Telegram vs Twitter)"""
    db = get_db()
    posts = db["posts"]
    
    # Parse dates
    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Query
    query = {"created_at": {"$gte": start_date, "$lte": end_date}}
    
    platforms = ["telegram", "twitter"]
    comparison = {}
    
    for platform in platforms:
        platform_query = {**query, "platform": platform}
        
        # Total posts
        total_posts = posts.count_documents(platform_query)
        
        # Days
        days = (end_date - start_date).days + 1
        avg_daily = total_posts / days if days > 0 else 0
        
        # Top topics
        topics_pipeline = [
            {"$match": platform_query},
            {"$unwind": "$topics"},
            {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        top_topics = [
            {"topic": t["_id"], "count": t["count"]}
            for t in posts.aggregate(topics_pipeline)
        ]
        
        comparison[platform] = {
            "total_posts": total_posts,
            "avg_daily": round(avg_daily, 1),
            "top_topics": top_topics
        }
    
    return {
        "comparison": comparison,
        "period": {
            "from": date_from,
            "to": date_to
        }
    }
