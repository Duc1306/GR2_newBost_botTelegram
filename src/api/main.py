from __future__ import annotations
from fastapi import FastAPI, Query, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
from src.db.mongo import get_db
from src.models.post import Post
from src.api.auth import (
    login, 
    get_current_user, 
    get_current_admin_user,
    get_current_user_token_data,
    LoginRequest,
    LoginResponse
)
from src.api.middleware import (
    setup_rate_limiting,
    setup_logging,
    log_requests_middleware,
    limiter
)
from loguru import logger

# Initialize logging first
setup_logging()

app = FastAPI(
    title="MXH Aggregator API",
    description="API tổng hợp tin tức từ Telegram & Twitter với ML Analytics",
    version="2.0.0"
)

# Setup rate limiting
setup_rate_limiting(app)

# Add request logging middleware
app.middleware("http")(log_requests_middleware)

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


# =============================================================================
# Authentication Endpoints (PUBLIC - No rate limit for critical auth)
# =============================================================================

@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login_endpoint(request: LoginRequest):
    """
    Login endpoint to get JWT token.
    
    **Credentials (default):**
    - Username: admin
    - Password: admin123
    
    **Response:**
    - access_token: JWT token to use in Authorization header
    - token_type: "bearer"
    - expires_in: Token expiration time in seconds
    - username: Authenticated username
    
    **Usage:**
    ```
    curl -X POST http://localhost:8000/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin123"}'
    ```
    """
    logger.info(f"Login attempt for user: {request.username}")
    result = login(request.username, request.password)
    logger.info(f"Login successful for user: {request.username}")
    return result

@app.post("/auth/logout", tags=["Authentication"])
async def logout_endpoint(current_user: str = Depends(get_current_user)):
    """
    Logout endpoint (token invalidation handled client-side).
    
    In JWT stateless setup, logout is handled by client removing the token.
    This endpoint is provided for consistency and logging purposes.
    """
    logger.info(f"Logout: {current_user}")
    return {"message": "Logged out successfully", "username": current_user}

@app.get("/auth/me", tags=["Authentication"])
async def get_current_user_info(token_data=Depends(get_current_user_token_data)):
    """
    Get current authenticated user info including role.
    Useful for frontend to verify token validity and determine role.
    """
    return {"username": token_data.username, "role": token_data.role, "authenticated": True}

# =============================================================================
# Public Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Trang chủ API"""
    return {
        "message": "🎉 MXH Aggregator API v2.0",
        "docs": "/docs",
        "security": {
            "authentication": "JWT Bearer Token or X-API-Key header",
            "login": "/auth/login",
            "default_credentials": "admin / admin123 (change in production!)"
        },
        "endpoints": {
            "auth": {
                "login": "/auth/login",
                "logout": "/auth/logout",
                "me": "/auth/me"
            },
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
    current_user: str = Depends(get_current_user)
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
    
    # Count UNIQUE posts with topics (not total topic assignments)
    labeled_posts_count = coll.count_documents({
        **base_query, 
        "topics": {"$exists": True, "$ne": []}
    })

    # Latest post theo filter
    latest = coll.find_one(base_query, sort=[("created_at", -1)])
    latest_date = latest["created_at"] if latest else None

    return {
        "total_posts": total_filtered,
        "labeled_posts": labeled_posts_count,  # NEW: unique posts with topics
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
    """Get trending topics (rising in popularity) - Using posts collection"""
    db = get_db()
    posts = db["posts"]
    
    # Calculate date range
    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    mid_date = end_date - timedelta(days=days//2)
    
    # Build platform query
    platform_filter = {} if platform == "all" else {"platform": platform}
    
    # Get recent posts by topic
    recent_pipeline = [
        {"$match": {
            "created_at": {"$gte": mid_date, "$lt": end_date},
            "topics": {"$exists": True, "$ne": []},
            **platform_filter
        }},
        {"$unwind": "$topics"},
        {"$group": {
            "_id": "$topics",
            "count": {"$sum": 1}
        }}
    ]
    recent_stats = list(posts.aggregate(recent_pipeline))
    
    # Get previous posts by topic
    previous_pipeline = [
        {"$match": {
            "created_at": {"$gte": start_date, "$lt": mid_date},
            "topics": {"$exists": True, "$ne": []},
            **platform_filter
        }},
        {"$unwind": "$topics"},
        {"$group": {
            "_id": "$topics",
            "count": {"$sum": 1}
        }}
    ]
    previous_stats = list(posts.aggregate(previous_pipeline))
    
    # Build lookup dictionaries
    recent_by_topic = {stat["_id"]: stat["count"] for stat in recent_stats}
    previous_by_topic = {stat["_id"]: stat["count"] for stat in previous_stats}
    
    # Calculate trends
    trends = []
    for topic, current_count in recent_by_topic.items():
        previous_count = previous_by_topic.get(topic, 0)
        
        # Calculate growth
        if previous_count > 0:
            growth_percentage = ((current_count - previous_count) / previous_count) * 100
            trend_score = current_count / previous_count
        else:
            growth_percentage = 100.0  # New topic
            trend_score = float('inf')
        
        # Determine direction
        if trend_score > 1.2 or previous_count == 0:
            trend_direction = "up"
        elif trend_score < 0.8:
            trend_direction = "down"
        else:
            trend_direction = "stable"
        
        trends.append({
            "topic": topic,
            "current_count": current_count,
            "previous_count": previous_count,
            "growth_percentage": round(growth_percentage, 1),
            "trend_direction": trend_direction,
            "trend_score": round(trend_score, 2) if trend_score != float('inf') else 999
        })
    
    # Sort by current count (most popular) and limit
    trends.sort(key=lambda x: x["current_count"], reverse=True)
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


@app.get("/analytics/heatmap")
async def get_activity_heatmap(
    date_from: Optional[str] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    topic: Optional[str] = Query(None, description="Lọc theo topic"),
):
    """
    Trả về activity heatmap: số lượng bài theo giờ trong ngày và ngày trong tuần
    """
    db = get_db()
    posts = db["posts"]
    
    # Parse dates
    if date_to:
        to_date = datetime.fromisoformat(date_to)
    else:
        to_date = datetime.utcnow()
    
    if date_from:
        from_date = datetime.fromisoformat(date_from)
    else:
        from_date = to_date - timedelta(days=30)
    
    # Build query
    query = {
        "created_at": {
            "$gte": from_date,
            "$lte": to_date
        }
    }
    
    if topic:
        query["topics"] = topic
    
    # Aggregate by hour and day of week
    pipeline = [
        {"$match": query},
        {
            "$project": {
                "hour": {"$hour": "$created_at"},
                "dayOfWeek": {"$dayOfWeek": "$created_at"}  # 1=Sunday, 2=Monday, ..., 7=Saturday
            }
        },
        {
            "$group": {
                "_id": {
                    "hour": "$hour",
                    "dayOfWeek": "$dayOfWeek"
                },
                "count": {"$sum": 1}
            }
        }
    ]
    
    results = list(posts.aggregate(pipeline))
    
    # Convert to heatmap format: heatmap[day][hour] = count
    # day: 0=Monday, 1=Tuesday, ..., 6=Sunday
    heatmap = {}
    for day in range(7):
        heatmap[day] = {}
        for hour in range(24):
            heatmap[day][hour] = 0
    
    for item in results:
        dow = item["_id"]["dayOfWeek"]
        hour = item["_id"]["hour"]
        count = item["count"]
        
        # Convert MongoDB dayOfWeek (1=Sunday) to our format (0=Monday)
        if dow == 1:  # Sunday
            day = 6
        else:  # Monday-Saturday
            day = dow - 2
        
        heatmap[day][hour] = count
    
    return {
        "heatmap": heatmap,
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        },
        "total_posts": sum(sum(hours.values()) for hours in heatmap.values())
    }

# =============================================================================
# Notifications Endpoints
# =============================================================================

@app.get("/notifications", tags=["Notifications"])
async def get_notifications(
    request: Request,
    unread_only: bool = Query(False, description="Only show unread notifications"),
    limit: int = Query(50, ge=1, le=100),
    current_user: str = Depends(get_current_user)
):
    """Get notifications for current user."""
    from src.models.notification import Notification
    
    db = get_db()
    coll = db["notifications"]
    
    query = {"user": current_user}
    if unread_only:
        query["read"] = False
    
    cursor = coll.find(query).sort("created_at", -1).limit(limit)
    notifications = []
    
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)
    
    return {
        "notifications": notifications,
        "unread_count": coll.count_documents({"user": current_user, "read": False})
    }

@app.post("/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_read(
    notification_id: str,
    current_user: str = Depends(get_current_user)
):
    """Mark a notification as read."""
    from bson import ObjectId
    
    db = get_db()
    coll = db["notifications"]
    
    result = coll.update_one(
        {"_id": ObjectId(notification_id), "user": current_user},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}

@app.post("/notifications/mark-all-read", tags=["Notifications"])
async def mark_all_read(current_user: str = Depends(get_current_user)):
    """Mark all notifications as read."""
    db = get_db()
    coll = db["notifications"]
    
    result = coll.update_many(
        {"user": current_user, "read": False},
        {"$set": {"read": True}}
    )
    
    return {"success": True, "updated": result.modified_count}

@app.delete("/notifications/{notification_id}", tags=["Notifications"])
async def delete_notification(
    notification_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a notification."""
    from bson import ObjectId
    
    db = get_db()
    coll = db["notifications"]
    
    result = coll.delete_one({"_id": ObjectId(notification_id), "user": current_user})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}

# =============================================================================
# Settings Endpoints
# =============================================================================

@app.get("/settings", tags=["Settings"])
async def get_settings(current_user: str = Depends(get_current_user)):
    """Get user settings."""
    from src.models.settings import UserSettings
    
    db = get_db()
    coll = db["user_settings"]
    
    settings = coll.find_one({"username": current_user})
    
    if not settings:
        # Create default settings
        default_settings = UserSettings(username=current_user).dict()
        coll.insert_one(default_settings)
        return default_settings
    
    settings.pop("_id", None)
    return settings

@app.put("/settings", tags=["Settings"])
async def update_settings(
    settings: dict,
    current_user: str = Depends(get_current_user)
):
    """Update user settings."""
    from src.models.settings import UpdateSettingsRequest
    
    db = get_db()
    coll = db["user_settings"]
    
    # Remove None values
    updates = {k: v for k, v in settings.items() if v is not None and k != "username"}
    
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    result = coll.update_one(
        {"username": current_user},
        {"$set": updates},
        upsert=True
    )
    
    logger.info(f"Settings updated for {current_user}: {list(updates.keys())}")
    
    return {"success": True, "updated_fields": list(updates.keys())}

# =============================================================================
# Hot Topics - Default seed data
# =============================================================================

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


# =============================================================================
# Public News Feed Endpoints (No Authentication Required)
# =============================================================================

@app.get("/public/posts", tags=["Public"])
@limiter.limit("200/minute")
async def get_public_posts(
    request: Request,
    q: Optional[str] = Query(None, description="Tìm kiếm trong nội dung"),
    keywords: Optional[str] = Query(None, description="Từ khóa (comma-separated)"),
    topic: Optional[str] = Query(None, description="Lọc theo topic"),
    lang: Optional[str] = Query(None, description="Ngôn ngữ (vi, en)"),
    link_only: bool = Query(False, description="Chỉ bài có link bên ngoài"),
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
        query["links"] = {"$exists": True, "$ne": []}

    if q:
        query["text"] = {"$regex": q, "$options": "i"}
    elif keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if kw_list:
            query["$or"] = [{"text": {"$regex": kw, "$options": "i"}} for kw in kw_list]

    projection = {
        "_id": 1, "id": 1, "text": 1, "source": 1, "author": 1,
        "created_at": 1, "links": 1, "topics": 1, "lang": 1,
        "full_article": 1, "platform": 1, "media": 1,
    }
    cursor = coll.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
    posts = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        posts.append(p)

    return posts


@app.get("/public/hot-topics", tags=["Public"])
async def get_public_hot_topics():
    """Return active hot topics list – no authentication required."""
    db = get_db()
    coll = db["hot_topics"]

    topics = list(coll.find({"active": True}, {"_id": 0}).sort("priority", 1))
    if not topics:
        return {"topics": DEFAULT_HOT_TOPICS, "seeded": False}

    return {"topics": topics, "seeded": True}


@app.get("/public/hot-topics/{slug}/posts", tags=["Public"])
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

    # Find topic in DB, fall back to defaults
    topic_doc = hot_topics_coll.find_one({"slug": slug, "active": True}, {"_id": 0})
    if not topic_doc:
        topic_doc = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)
    if not topic_doc:
        raise HTTPException(status_code=404, detail="Hot topic not found")

    keywords = topic_doc.get("keywords", [])
    if not keywords:
        return {"topic": topic_doc, "posts": [], "total": 0, "skip": skip, "limit": limit}

    query = {"$or": [{"text": {"$regex": kw, "$options": "i"}} for kw in keywords]}
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


# =============================================================================
# Admin: Hot Topics Management
# =============================================================================

@app.post("/admin/hot-topics/seed", tags=["Admin"])
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


@app.get("/admin/hot-topics", tags=["Admin"])
async def admin_list_hot_topics(current_user: str = Depends(get_current_admin_user)):
    """Admin: list all hot topics (including inactive)."""
    db = get_db()
    topics = list(db["hot_topics"].find({}, {"_id": 0}).sort("priority", 1))
    return {"topics": topics}


@app.post("/admin/hot-topics", tags=["Admin"])
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

    if coll.find_one({"slug": topic["slug"]}):
        raise HTTPException(status_code=409, detail="Slug already exists")

    doc = {
        "slug": topic["slug"],
        "name": topic["name"],
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


@app.put("/admin/hot-topics/{slug}", tags=["Admin"])
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

    result = coll.update_one({"slug": slug}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hot topic not found")

    return {"success": True}


@app.delete("/admin/hot-topics/{slug}", tags=["Admin"])
async def admin_delete_hot_topic(
    slug: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: delete a hot topic."""
    db = get_db()
    result = db["hot_topics"].delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hot topic not found")
    return {"success": True}


# =============================================================================
# Admin: AI-powered Hot Topics Endpoints
# =============================================================================

@app.get("/admin/ai/status", tags=["AI"])
async def ai_status(current_user: str = Depends(get_current_admin_user)):
    """Check whether OpenAI is configured and reachable."""
    from src.processing.ai_topic_detector import check_openai_status
    return check_openai_status()


@app.post("/admin/ai/detect-hot-topics", tags=["AI"])
async def ai_detect_hot_topics(
    hours: int = Query(24, ge=1, le=168, description="Look at posts from the last N hours"),
    max_topics: int = Query(5, ge=1, le=10, description="Max new topics to suggest"),
    auto_save: bool = Query(False, description="Automatically save suggestions to DB (inactive by default)"),
    current_user: str = Depends(get_current_admin_user),
):
    """
    Use GPT-4o-mini to analyse recent posts and suggest NEW hot topics.

    The AI reads up to 80 recent posts and identifies emerging topics not already
    tracked. Topics are saved as **inactive** (admin must activate them).

    Requires OPENAI_API_KEY in environment variables.
    """
    from src.processing.ai_topic_detector import detect_new_hot_topics
    db = get_db()

    # Fetch recent posts
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cursor = db["posts"].find(
        {"created_at": {"$gte": cutoff}},
        {"text": 1, "_id": 0},
    ).sort("created_at", -1).limit(80)
    posts = list(cursor)

    if not posts:
        return {"suggestions": [], "message": "No posts found in the given time window"}

    # Get existing slugs to avoid re-suggesting already tracked topics
    existing_slugs = [t["slug"] for t in db["hot_topics"].find({}, {"slug": 1, "_id": 0})]

    suggestions = detect_new_hot_topics(
        posts,
        existing_slugs=existing_slugs,
        max_new_topics=max_topics,
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


@app.post("/admin/ai/expand-keywords/{slug}", tags=["AI"])
async def ai_expand_keywords(
    slug: str,
    current_user: str = Depends(get_current_admin_user),
):
    """
    Use GPT-4o-mini to expand the keyword list for an existing hot topic.

    Automatically updates the topic's keywords in the database.
    Requires OPENAI_API_KEY.
    """
    from src.processing.ai_topic_detector import expand_keywords
    db = get_db()
    coll = db["hot_topics"]

    topic = coll.find_one({"slug": slug}, {"_id": 0})
    if not topic:
        # Try defaults
        topic = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)
        if not topic:
            raise HTTPException(status_code=404, detail="Hot topic not found")

    original_keywords = topic.get("keywords", [])
    expanded = expand_keywords(topic["name"], original_keywords)

    new_count = len(expanded) - len(original_keywords)

    # Persist to DB
    coll.update_one(
        {"slug": slug},
        {"$set": {"keywords": expanded, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

    return {
        "slug": slug,
        "original_count": len(original_keywords),
        "expanded_count": len(expanded),
        "new_keywords_added": new_count,
        "keywords": expanded,
    }


@app.get("/public/hot-topics/{slug}/posts/ai", tags=["Public"])
@limiter.limit("30/minute")
async def get_hot_topic_posts_ai(
    request: Request,
    slug: str,
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """
    Like /public/hot-topics/{slug}/posts but re-ranks results using OpenAI embeddings
    for more semantically relevant ordering. Falls back to keyword ordering if OpenAI
    is not configured.

    This endpoint is intentionally rate-limited (30/min) due to embedding cost.
    """
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

    # Fetch more candidates than needed so embedding re-ranking has material to work with
    fetch_limit = min((skip + limit) * 3, 150)
    cursor = posts_coll.find(keyword_query, projection).sort("created_at", -1).limit(fetch_limit)
    candidates = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        candidates.append(p)

    # Build query text for embedding
    query_text = (
        f"{topic_doc['name']}. {topic_doc.get('description', '')}. "
        f"Keywords: {', '.join(keywords[:15])}"
    )

    ranked = score_posts_by_embedding(candidates, query_text)
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


@app.post("/settings/change-password", tags=["Settings"])
async def change_password(
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Change user password."""
    from src.config import ADMIN_USERNAME, ADMIN_PASSWORD
    from src.api.auth import authenticate_user, get_password_hash
    
    current_password = request.get("current_password")
    new_password = request.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")
    
    # Verify current password
    if not authenticate_user(current_user, current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    # In production, update in database
    # For now, just log it
    logger.info(f"Password change requested for {current_user}")
    
    return {
        "message": "Password changed successfully! (Demo mode - not persisted)"
    }
