from __future__ import annotations
import re
import io
import base64
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Depends, Security, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
from src.db.mongo import get_db, get_users_collection
from src.models.post import Post
from src.models.user import UserPublic, UpdateUserStatusRequest, UpdateUserRoleRequest
from src.api.auth import (
    login,
    register_user,
    get_current_user,
    get_current_admin_user,
    get_current_user_token_data,
    LoginRequest,
    LoginResponse
)
from src.models.user import RegisterRequest
from src.api.middleware import (
    setup_rate_limiting,
    setup_logging,
    log_requests_middleware,
    limiter
)
from src.config import get_allowed_origins, GOOGLE_CLIENT_ID
from src.api.channels import router as channels_router
from src.api.telegram_auth import router as telegram_auth_router
from loguru import logger

# Initialize logging first
setup_logging()

# ---------------------------------------------------------------------------
# In-memory hotnews cache — prevents duplicate GPT calls for concurrent
# requests with the same (hours, bucket) key.
# TTL matches bucket_size: 1h for 24h window, 2h for 48h, 3h for 72h+.
# ---------------------------------------------------------------------------
_hotnews_mem: dict[str, dict] = {}          # cache_key → {"result": ..., "ts": datetime}
_hotnews_locks: dict[str, asyncio.Lock] = {}  # cache_key → Lock (one GPT call at a time)

def _hotnews_mem_ttl(hours: int) -> timedelta:
    if hours <= 24:
        return timedelta(hours=1)
    elif hours <= 48:
        return timedelta(hours=2)
    return timedelta(hours=3)


def _cleanup_hotnews_cache() -> None:
    """Remove expired entries from in-memory cache and orphaned locks."""
    now = datetime.utcnow()
    expired = []
    for k, v in list(_hotnews_mem.items()):
        try:
            hours = int(k.split(':')[1])
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background workers when the API boots; cancel them on shutdown."""
    from scripts.create_indexes import create_indexes
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, create_indexes)
    from src.ingestion.channel_queue_worker import run_worker, run_refresh_loop
    pending_task = asyncio.create_task(run_worker())
    refresh_task = asyncio.create_task(run_refresh_loop())
    precompute_task = asyncio.create_task(_hotnews_precompute_worker())
    logger.info("Background workers started (pending-queue poller + active-channel refresher + hotnews warmer).")
    try:
        yield
    finally:
        pending_task.cancel()
        refresh_task.cancel()
        precompute_task.cancel()
        logger.info("Background workers stopped.")


app = FastAPI(
    title="MXH Aggregator API",
    description="API tổng hợp tin tức từ Telegram & Twitter với ML Analytics",
    version="2.0.0",
    lifespan=lifespan,
)

# Setup rate limiting
setup_rate_limiting(app)

# Add request logging middleware
app.middleware("http")(log_requests_middleware)

# CORS middleware để frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(channels_router)
app.include_router(telegram_auth_router)


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


@app.post("/auth/register", tags=["Authentication"])
async def register_endpoint(request: RegisterRequest):
    """Đăng ký tài khoản mới (role=user, status=active)."""
    result = register_user(request)
    logger.info(f"New user registered: {result['username']}")
    token_data = login(result["username"], request.password)
    return token_data


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
    Get current authenticated user info including role and profile.
    Useful for frontend to verify token validity and determine role.
    """
    users_col = get_users_collection()
    user_doc = users_col.find_one({"username": token_data.username})
    profile = {}
    if user_doc:
        profile = {
            "full_name": user_doc.get("full_name"),
            "email": user_doc.get("email"),
            "phone_number": user_doc.get("phone_number"),
            "telegram_username": user_doc.get("telegram_username"),
            "telegram_linked": bool(user_doc.get("telegram_session")),
        }
    return {
        "username": token_data.username,
        "role": token_data.role,
        "authenticated": True,
        **profile,
    }


# ---------------------------------------------------------------------------
# Google OAuth login
# ---------------------------------------------------------------------------
from pydantic import BaseModel as _BM

class GoogleTokenRequest(_BM):
    id_token: str


@app.post("/auth/google", tags=["Authentication"])
async def google_oauth_login(body: GoogleTokenRequest):
    """
    Xác thực bằng Google Sign-In.
    Frontend gửi id_token từ Google, hệ thống trả về JWT nội bộ.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth chưa được cấu hình trên máy chủ.")

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Google token không hợp lệ: {exc}")

    google_email: str = id_info.get("email", "")
    google_name: str = id_info.get("name", "")
    google_sub: str = id_info.get("sub", "")

    if not google_email:
        raise HTTPException(status_code=400, detail="Không lấy được email từ tài khoản Google.")

    users_col = get_users_collection()
    user_doc = users_col.find_one({"email": google_email})

    if user_doc is None:
        # Auto-create account for new Google users
        from src.api.auth import get_password_hash
        import secrets
        username_base = google_email.split("@")[0].replace(".", "_")[:28]
        # Ensure uniqueness
        username = username_base
        suffix = 1
        while users_col.find_one({"username": username}):
            username = f"{username_base}_{suffix}"
            suffix += 1

        user_doc = {
            "username": username,
            "email": google_email,
            "full_name": google_name or username,
            "password_hash": get_password_hash(secrets.token_hex(32)),
            "role": "user",
            "status": "active",
            "google_sub": google_sub,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
        }
        users_col.insert_one(user_doc)
        logger.info(f"New Google user auto-registered: {username} ({google_email})")
    else:
        username = user_doc["username"]
        users_col.update_one({"_id": user_doc["_id"]}, {"$set": {"last_login": datetime.utcnow()}})

    from src.api.auth import create_access_token
    from datetime import timedelta
    from src.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    role = user_doc.get("role", "user")
    access_token = create_access_token(
        {"sub": username, "role": role},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"Google login successful: {username}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": username,
        "role": role,
    }

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
        query["$text"] = {"$search": q}
    if link_only:
        query["links"] = {"$exists": True, "$ne": []}
    
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
    platform: Optional[str] = Query("all", description="Filter by platform"),
    current_user: str = Depends(get_current_user)
):
    """Đếm số lượng bài viết"""
    db = get_db()
    coll = db["posts"]
    
    query = {}
    if platform and platform != "all":
        query["platform"] = platform
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
    platform: Optional[str] = Query("all", description="Filter by platform"),
    current_user: str = Depends(get_current_user)
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
    platform: Optional[str] = Query("all", description="Filter by platform"),
    current_user: str = Depends(get_current_user)
):
    """Thống kê tổng quan (có thể lọc theo link/topic/ngôn ngữ)."""
    db = get_db()
    coll = db["posts"]

    base_query: dict = {}
    if platform and platform != "all":
        base_query["platform"] = platform
    if link_only:
        base_query["links"] = {"$exists": True, "$ne": []}
    if topics_only:
        # Đảm bảo có ít nhất 1 phần tử trong topics
        base_query["topics"] = {"$exists": True, "$ne": []}
    if lang:
        base_query["lang"] = lang

    # Single $facet pipeline: all stats in one collection scan
    facet_result = list(coll.aggregate([
        {"$match": base_query},
        {"$facet": {
            "total": [{"$count": "n"}],
            "sources": [
                {"$group": {"_id": "$source", "count": {"$sum": 1}}}
            ],
            "languages": [
                {"$group": {"_id": "$lang", "count": {"$sum": 1}}}
            ],
            "topics": [
                {"$match": {"topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ],
            "platforms": [
                {"$group": {"_id": "$platform", "count": {"$sum": 1}}}
            ],
            "labeled_count": [
                {"$match": {"topics": {"$exists": True, "$ne": []}}},
                {"$count": "count"}
            ],
            "latest": [
                {"$sort": {"created_at": -1}},
                {"$limit": 1},
                {"$project": {"created_at": 1}}
            ],
        }}
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

    # Normalise: "twitter" → "x", None/missing → "telegram"
    _PLATFORM_MAP = {"twitter": "x", "x": "x", "telegram": "telegram"}
    by_platform: dict = {"telegram": 0, "x": 0}
    for p in platforms:
        raw_key = (p["_id"] or "telegram").lower()
        key = _PLATFORM_MAP.get(raw_key, raw_key)
        by_platform[key] = by_platform.get(key, 0) + p["count"]

    # Count active channels (2 fast indexed queries)
    channels_coll = db["channels"]
    channel_meta_coll = db["channel_metadata"]
    active_channels_telegram = channel_meta_coll.count_documents({"platform": "telegram"})
    active_channels_x = channels_coll.count_documents({"status": "active", "platform": {"$in": ["x", "twitter"]}})

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
        "latest_post_date": latest_date
    }


@app.get("/posts/{post_id}")
async def get_post_by_id(post_id: str, current_user: str = Depends(get_current_user)):
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
    
    # Single $facet pipeline for both halves
    facet_result = list(posts.aggregate([
        {"$match": {
            "created_at": {"$gte": start_date, "$lt": end_date},
            "topics": {"$exists": True, "$ne": []},
            **platform_filter
        }},
        {"$facet": {
            "recent": [
                {"$match": {"created_at": {"$gte": mid_date}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
            ],
            "previous": [
                {"$match": {"created_at": {"$lt": mid_date}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
            ],
        }}
    ]))
    facet = facet_result[0] if facet_result else {}
    
    # Build lookup dictionaries
    recent_by_topic = {s["_id"]: s["count"] for s in facet.get("recent", [])}
    previous_by_topic = {s["_id"]: s["count"] for s in facet.get("previous", [])}
    
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
    
    days = (end_date - start_date).days + 1

    # Single $facet: counts + top topics for both platforms in one scan
    facet_result = list(posts.aggregate([
        {"$match": query},
        {"$facet": {
            "telegram_count": [
                {"$match": {"platform": "telegram"}},
                {"$count": "n"},
            ],
            "telegram_topics": [
                {"$match": {"platform": "telegram", "topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5},
            ],
            "twitter_count": [
                {"$match": {"platform": "twitter"}},
                {"$count": "n"},
            ],
            "twitter_topics": [
                {"$match": {"platform": "twitter", "topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5},
            ],
        }}
    ]))
    f = facet_result[0] if facet_result else {}

    comparison = {}
    for plat in ["telegram", "twitter"]:
        total_posts = (f.get(f"{plat}_count", [{}])[0] or {}).get("n", 0)
        top_topics = [
            {"topic": t["_id"], "count": t["count"]}
            for t in f.get(f"{plat}_topics", [])
        ]
        comparison[plat] = {
            "total_posts": total_posts,
            "avg_daily": round(total_posts / days, 1) if days > 0 else 0,
            "top_topics": top_topics,
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
        # Only posts that have at least one external (non-t.me) link
        query["links"] = {"$elemMatch": {"$regex": "^https?://", "$not": {"$regex": "t\\.me"}}}

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


# ─── Topic palette (shared across endpoints) ─────────────────────────────────
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


@app.get("/public/post-topics", tags=["Public"])
@limiter.limit("120/minute")
async def get_public_post_topics(request: Request):
    """
    Return distinct ML-classified topic categories that appear in posts
    which have at least one external link.  Used by the user articles tab
    to populate topic filter chips.
    """
    db = get_db()
    posts_coll = db["posts"]

    pipeline = [
        {
            "$match": {
                # Only count posts with at least one real external (non-t.me) link
                "links": {"$elemMatch": {"$regex": "^https?://", "$not": {"$regex": "t\\.me"}}},
                "topics": {"$exists": True, "$ne": []},
            }
        },
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
                t["_id"]
                .lower()
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
    """Convert Vietnamese ML topic name to a URL-safe slug."""
    import re, unicodedata
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# ─── Hotnews pipeline helpers ─────────────────────────────────────────────────

async def _compute_hotnews_clusters(db, hours: int, now: datetime, cache_key: str) -> list[dict]:
    """
    Core hotnews pipeline: fetch posts → DBSCAN+GPT clustering → ML fallback → cache.

    Extracted so both the endpoint (cold-start) and the background pre-warm
    worker can call it without duplicating code.

    Caller MUST hold _get_hotnews_lock(cache_key) before calling.
    """
    import re as _re
    import math as _math
    from src.processing.ai_topic_detector import (
        filter_relevant_posts, discover_hot_events,
        cluster_and_summarize as _cas, gpt_name_ml_clusters,
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
    RECENT_SPAN   = min(hours, 24)
    RECENT_SLICES = 3
    RECENT_PPL    = 150
    all_posts: list[dict] = []
    seen_ids: set = set()

    recent_slice_h = _math.ceil(RECENT_SPAN / RECENT_SLICES)
    for i in range(RECENT_SLICES):
        slice_end   = now - timedelta(hours=i * recent_slice_h)
        slice_start = now - timedelta(hours=(i + 1) * recent_slice_h)
        if slice_start < since:
            slice_start = since
        for p in posts_coll.find(
            {"created_at": {"$gte": slice_start, "$lt": slice_end}}, projection,
        ).sort("created_at", -1).limit(RECENT_PPL):
            pid = str(p["_id"])
            if pid not in seen_ids:
                seen_ids.add(pid); p["_id"] = pid; all_posts.append(p)

    if hours > 24:
        older_start = since
        older_end   = now - timedelta(hours=24)
        older_limit = 150 * max(1, (hours - 24) // 24)
        for p in posts_coll.find(
            {"created_at": {"$gte": older_start, "$lt": older_end}}, projection,
        ).sort("created_at", -1).limit(older_limit):
            pid = str(p["_id"])
            if pid not in seen_ids:
                seen_ids.add(pid); p["_id"] = pid; all_posts.append(p)

    # Cap before DBSCAN (O(n²) distance matrix)
    _EMBED_CAP = 450
    if len(all_posts) > _EMBED_CAP:
        _wl = [p for p in all_posts if p.get("links")]
        _nl = [p for p in all_posts if not p.get("links")]
        logger.info("hotnews: capped all_posts %d→%d", len(all_posts), _EMBED_CAP)
        all_posts = (_wl + _nl)[:_EMBED_CAP]

    clusters: list[dict] = []

    # ── Step 2: Embedding clustering (PRIMARY) ────────────────────────────────
    async def _build_cluster(ev: dict) -> dict | None:
        ev_posts = ev.get("posts", [])
        if len(ev_posts) < 2:
            return None

        # Anchor-based filter: use the richest article's actual text as semantic
        # anchor instead of the GPT-generated cluster name. The anchor text is far
        # more specific (e.g. full article title+body) → higher precision at 0.50.
        try:
            _anchor = next((p for p in ev_posts if p.get("links")), ev_posts[0])
            _fa = _anchor.get("full_article") or {}
            _anchor_text = (
                (_fa.get("title") or "")
                + " "
                + (_fa.get("body") or _anchor.get("text") or "")
            )[:600].strip()
            _filter_query = _anchor_text if len(_anchor_text) > 60 else ev["name"]
            event_filtered = await filter_relevant_posts(
                ev_posts, topic_name=_filter_query, threshold=0.50, top_k=15,
            )
            if len(event_filtered) < 2:
                logger.info(
                    "_build_cluster: anchor filter too strict for %r (%d→%d), keeping original",
                    ev["name"], len(ev_posts), len(event_filtered),
                )
                event_filtered = ev_posts[:15]
        except Exception as _fe:
            logger.warning("_build_cluster: filter failed: %s", _fe)
            event_filtered = ev_posts[:15]

        # Sort: link-rich posts first; strip internal embedding/score fields
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

        # Background summary (non-blocking)
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
                            {"key": _re.compile(f"^audio:{_re.escape(_slug)}")}
                        )
                        logger.info("_bg_summary: done slug=%s posts=%d", _slug, len(_gpt_validated))
                        # Pre-generate audio so user gets instant playback
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

    # ── Step 3: ML-topic velocity fallback (fill if < 4 embedding clusters) ───
    if len(clusters) < 4:
        from src.processing.ai_topic_detector import gpt_name_ml_clusters

        velocity_pipeline = [
            {"$match": {"created_at": {"$gte": since}, "topics": {"$exists": True, "$ne": []}}},
            {"$unwind": "$topics"},
            {"$group": {
                "_id": "$topics",
                "count": {"$sum": 1},
                "with_links": {"$sum": {"$cond": [
                    {"$gt": [{"$size": {"$ifNull": ["$links", []]}}, 0]}, 1, 0
                ]}},
                "latest": {"$max": "$created_at"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 8},
        ]
        trending = list(posts_coll.aggregate(velocity_pipeline))
        existing_slugs = {c["slug"] for c in clusters}

        ml_raw_clusters = []
        for item in trending:
            if len(clusters) + len(ml_raw_clusters) >= 8:
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

            filtered = await filter_relevant_posts(sorted_posts, topic_name=topic_name, top_k=15)
            if not filtered:
                continue
            for p in filtered:
                p.pop("_emb", None); p.pop("_ai_score", None)

            filtered = sorted(filtered, key=lambda p: (not bool(p.get("links")), 0))
            latest = filtered[0].get("created_at")
            latest_str = latest.isoformat() if hasattr(latest, "isoformat") else str(latest or "")
            headline = (
                (filtered[0].get("full_article") or {}).get("title")
                or (filtered[0].get("text") or "")[:120]
            )
            ml_raw_clusters.append({
                "slug": slug,
                "topic_name": topic_name,
                "color": _ML_TOPIC_COLORS.get(topic_name, "#6b7280"),
                "post_count": len(filtered),
                "posts_with_links": len([p for p in filtered if any(
                    l.startswith("http") and "t.me" not in l
                    for l in (p.get("links") or [])
                )]),
                "latest_at": latest_str,
                "headline": headline,
                "posts": filtered[:15],
            })
            existing_slugs.add(slug)

        ml_named = await gpt_name_ml_clusters(ml_raw_clusters)
        for cl in ml_named:
            clusters.append({
                "slug": cl["slug"],
                "name": cl["name"],
                "description": cl.get("description", ""),
                "color": cl.get("color", "#6b7280"),
                "post_count": cl["post_count"],
                "posts_with_links": cl["posts_with_links"],
                "latest_at": cl["latest_at"],
                "headline": cl["headline"],
                "posts": cl["posts"],
                "source": "ml_velocity",
                "broad_topic": cl["topic_name"],
            })

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
    """
    Background task: compute and cache a new hotnews bucket without blocking
    the request that triggered it (stale-while-revalidate pattern).
    """
    lock = _get_hotnews_lock(cache_key)
    if lock.locked():
        return  # Already computing by another request
    async with lock:
        db = get_db()
        # Double-check after acquiring the lock
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
    """
    Background worker: pre-warm the 24h hotnews cache so users never hit
    a cold-start wait. Checks every 5 minutes; pre-computes the next bucket
    10 minutes before it would transition.
    """
    await asyncio.sleep(120)  # Let API fully start
    while True:
        try:
            now = datetime.utcnow()
            db = get_db()
            cache_coll = db["hotnews_v2_cache"]
            for hours in [24]:
                bucket_size = 1  # 24h window → 1h buckets
                bucket_hour = (now.hour // bucket_size) * bucket_size
                cache_key = f"hotnews_kw:{hours}:{now.strftime('%Y%m%d')}{bucket_hour:02d}"

                # Current bucket not computed yet → compute it
                if not cache_coll.find_one({"key": cache_key}, {"_id": 1}):
                    logger.info("hotnews warmer: computing missing bucket %s", cache_key)
                    asyncio.create_task(_bg_ensure_hotnews_cached(hours, cache_key, now))
                    continue

                # Near bucket boundary? Pre-compute the NEXT bucket.
                mins_past = now.minute % (bucket_size * 60)
                mins_left = (bucket_size * 60) - mins_past
                if mins_left <= 10:
                    next_now = now + timedelta(minutes=mins_left + 1)
                    next_bh  = (next_now.hour // bucket_size) * bucket_size
                    next_key = f"hotnews_kw:{hours}:{next_now.strftime('%Y%m%d')}{next_bh:02d}"
                    if not cache_coll.find_one({"key": next_key}, {"_id": 1}):
                        logger.info("hotnews warmer: pre-computing next bucket %s", next_key)
                        asyncio.create_task(_bg_ensure_hotnews_cached(hours, next_key, next_now))
        except Exception as exc:
            logger.exception("hotnews precompute worker error: %s", exc)
        await asyncio.sleep(300)  # Check every 5 minutes


@app.get("/public/hotnews", tags=["Public"])
@limiter.limit("120/minute")
async def get_public_hotnews(
    request: Request,
    hours: int = Query(48, ge=1, le=168, description="Look-back window in hours"),
):
    """
    Return hot-news clusters driven by embedding-based event clustering.

    Flow:
    1. Fetch recent posts (24h dense + optional older window).
    2. Batch-embed all posts → DBSCAN semantic clusters → GPT event naming.
    3. Anchor-based relevance filter (threshold 0.50, reusing pre-computed embeddings).
    4. If < 4 clusters, fill from ML-topic velocity fallback.
    5. Cache per (hours, bucket). Stale-while-revalidate for bucket transitions.
    """
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

    # ── L1: in-memory cache (instant, no DB round-trip) ──────────────────────
    mem = _hotnews_mem.get(cache_key)
    if mem and (now - mem["ts"]) < _hotnews_mem_ttl(hours):
        return {**mem["result"], "cached": True}

    # ── L2: MongoDB cache ─────────────────────────────────────────────────────
    cached = cache_coll.find_one({"key": cache_key})
    if cached and cached.get("clusters"):
        result = {"clusters": cached["clusters"], "since": since.isoformat(), "hours": hours, "cached": True}
        _hotnews_mem[cache_key] = {"result": result, "ts": datetime.utcnow()}
        return result

    # ── L3: compute — stale-while-revalidate ──────────────────────────────────
    # If another request is already holding the compute lock, return the most
    # recent cached result from any bucket immediately (don't queue behind it).
    import re as _re_swr
    lock = _get_hotnews_lock(cache_key)
    if lock.locked():
        prev = cache_coll.find_one(
            {"clusters": {"$exists": True, "$ne": []}},
            sort=[("created_at", -1)],
        )
        if prev and prev.get("clusters"):
            return {"clusters": prev["clusters"], "since": since.isoformat(),
                    "hours": hours, "cached": True, "refreshing": True}

    # If there's a previous bucket result (different key), serve it NOW and
    # compute the new bucket silently in the background.
    prev_cached = cache_coll.find_one(
        {
            "key": _re_swr.compile(f"^hotnews_kw:{hours}:"),
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

    # No previous result available — must compute synchronously (cold start only).
    async with lock:
        # Double-check after acquiring lock (another coroutine may have finished)
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



@app.post("/public/hotnews/{slug}/summary", tags=["Public"])
@limiter.limit("30/minute")
async def get_hotnews_summary(
    request: Request,
    slug: str,
    hours: int = Query(48, ge=1, le=168),
):
    """
    Use OpenAI to summarise all recent posts for a hot-topic cluster.

    Works with both:
    - ML-velocity slugs (e.g. ``the-thao``, ``cong-nghe``) — posts looked up by ML topics field
    - Legacy hot_topics slugs (e.g. ``iran-israel``) — posts looked up by keywords

    Results are cached for 30 minutes.
    """
    from src.processing.ai_topic_detector import cluster_and_summarize  # noqa: F811 (also imported in refresh path)

    db = get_db()
    cache_coll = db["hotnews_summary_cache"]
    posts_coll = db["posts"]

    def _extract_link_posts(posts: list[dict]) -> list[dict]:
        """Return structured list of all posts, with url=None when no external link."""
        result = []
        for p in posts:
            links = p.get("links") or []
            fa = p.get("full_article") or {}
            # First: prefer a non-t.me HTTP URL from the links list
            url = next((l for l in links if l.startswith("http") and "t.me" not in l), None)
            # Fallback: use full_article.url if available (scraped article URL)
            if not url:
                fa_url = fa.get("url", "")
                if fa_url and fa_url.startswith("http") and "t.me" not in fa_url:
                    url = fa_url
            title = fa.get("title") or (p.get("text") or "")[:120]
            snippet = (p.get("text") or "")[:200]
            source = p.get("source") or p.get("channel_username") or ""
            result.append({"title": title, "url": url, "source": source, "snippet": snippet})
        return result

    # Check cache (30-min TTL) — exact (slug, hours) key only, no cross-hours fallback.
    # Cross-hours reuse caused 48h summaries (30 posts) to appear for 24h requests.
    cache_key = f"{slug}:{hours}:v2"
    cached = cache_coll.find_one({"key": cache_key})
    if cached and cached.get("expires_at") and cached["expires_at"] > datetime.utcnow():
        # Guard: if cached post_count is suspiciously low (stale from old buggy code), recompute
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

    # ── Try ML-velocity slug first: reverse-map slug → ML topic name ──────────
    ml_topic_name = next(
        (name for name in _ML_TOPIC_COLORS if _ml_topic_slug(name) == slug),
        None,
    )

    if ml_topic_name:
        # Prefer posts from the pre-built embedding cluster (same posts shown on the card).
        # Fall back to a fresh ML topic query only when no cluster exists in cache.
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
            # No cluster in cache — query by ML topic within the requested window
            raw = list(
                posts_coll.find({"created_at": {"$gte": since}, "topics": ml_topic_name}, proj)
                .sort("created_at", -1).limit(20)
            )
            has_link = [p for p in raw if p.get("links")]
            no_link  = [p for p in raw if not p.get("links")]
            posts = (has_link + no_link)[:15]
        topic_display_name = ml_topic_name
    else:
        # Fallback: look up legacy hot_topics collection or AI-discovered cluster
        hot_topics_coll = db["hot_topics"]
        topic_doc = hot_topics_coll.find_one({"slug": slug, "active": True}, {"_id": 0})
        if not topic_doc:
            topic_doc = next((t for t in DEFAULT_HOT_TOPICS if t["slug"] == slug), None)

        # Check hotnews_v2_cache for embedding-clustered or keyword-trend events
        if not topic_doc:
            cutoff = datetime.utcnow() - timedelta(hours=max(hours, 6))
            hn_cached = db["hotnews_v2_cache"].find_one(
                {"clusters.slug": slug, "created_at": {"$gte": cutoff}},
                sort=[("created_at", -1)],
            )
            if hn_cached:
                cluster = next((c for c in (hn_cached.get("clusters") or []) if c["slug"] == slug), None)
                if cluster:
                    # Summary was pre-computed in _build_cluster → should already be in cache.
                    # If for some reason it's missing, compute it now (once) and cache it.
                    posts = cluster.get("posts", [])[:15]
                    topic_display_name = cluster["name"]
                    import asyncio as _asyncio
                    result = await cluster_and_summarize(posts, topic_display_name)
                    result.pop("_filtered_posts", None)
                    link_posts = _extract_link_posts(posts)
                    expires_at = datetime.utcnow() + timedelta(minutes=30)
                    cache_coll.update_one({"key": cache_key}, {"$set": {**result, "key": cache_key, "post_count": len(posts), "link_posts": link_posts, "expires_at": expires_at}}, upsert=True)
                    db["hotnews_audio_cache"].delete_many({"key": re.compile(f"^audio:{re.escape(slug)}")})
                    return {"slug": slug, **result, "cached": False, "post_count": len(posts), "link_posts": link_posts}

        if not topic_doc:
            raise HTTPException(status_code=404, detail="Hot topic not found")

        keywords = topic_doc.get("keywords", [])
        if not keywords:
            return {"slug": slug, "title": "", "lead": "", "body": [], "conclusion": "", "key_points": [], "sentiment": "neutral", "post_count": 0}

        query = {
            "$and": [
                {"created_at": {"$gte": since}},
                {"$or": [{"text": {"$regex": kw, "$options": "i"}} for kw in keywords]},
            ]
        }
        posts = list(posts_coll.find(query, proj).sort("created_at", -1).limit(30))
        topic_display_name = topic_doc["name"]

    if not posts:
        return {"slug": slug, "title": "", "lead": "", "body": [], "conclusion": "", "key_points": [], "sentiment": "neutral", "post_count": 0, "link_posts": []}

    # Run blocking OpenAI call in thread pool to avoid blocking the async event loop
    import asyncio
    result = await cluster_and_summarize(posts, topic_display_name)
    result.pop("_filtered_posts", None)  # dùng nội bộ để viết bài, không hiển thị
    link_posts = _extract_link_posts(posts)  # posts đã qua embedding filter → đủ sạch

    # Cache result
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
    # Xóa audio cache cũ khi summary mới được tạo (để audio được re-generate với nội dung mới)
    db["hotnews_audio_cache"].delete_many({"key": re.compile(f"^audio:{re.escape(slug)}")})  # xóa TẤT CẢ audio cache của slug này

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


# =============================================================================
# TTS – Audio endpoint
# =============================================================================

async def _generate_tts_bytes(text: str) -> bytes:
    """Dùng edge-tts tạo file MP3 từ văn bản, voice tiếng Việt HoaiMy."""
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts chưa được cài. Chạy: pip install edge-tts")

    communicate = edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural")
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


async def _bg_pregenerate_audio(slug: str, summary_doc: dict) -> None:
    """
    Background task: pre-generate TTS audio right after a summary is saved.
    When the user clicks the audio button, the MP3 is already in cache → instant playback.
    """
    try:
        db = get_db()
        audio_cache = db["hotnews_audio_cache"]
        now = datetime.utcnow()

        # Build the same cache key the audio endpoint uses
        expires_at = summary_doc.get("expires_at")
        summary_bucket = expires_at.strftime("%Y%m%d%H%M") if expires_at else "x"
        cache_key = f"audio:{slug}:{summary_bucket}"

        # Skip if already cached
        if audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}}, {"_id": 1}):
            return

        # Assemble TTS text (same logic as the audio endpoint)
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


@app.get("/public/hotnews/{slug}/audio", tags=["Public"])
@limiter.limit("10/minute")
async def get_hotnews_audio(
    request: Request,
    slug: str,
    hours: int = Query(48, ge=1, le=168),
):
    """
    Trả về file MP3 (TTS) tóm tắt tin nóng cho slug chỉ định.
    Dùng Microsoft Edge TTS (edge-tts), voice vi-VN-HoaiMyNeural.
    Kết quả được cache trong MongoDB collection hotnews_audio_cache (TTL 2h).
    """
    db = get_db()
    audio_cache = db["hotnews_audio_cache"]
    summary_cache = db["hotnews_summary_cache"]

    now = datetime.utcnow()

    # ── Tìm summary trước để lấy nội dung VÀ làm cache key ───────────────────
    # cache key gắn theo expires_at của summary → audio tự invalidate khi summary mới
    summary_doc = summary_cache.find_one(
        {"key": re.compile(f"^{re.escape(slug)}:\\d+:v2$"), "expires_at": {"$gt": now}},
        sort=[("expires_at", -1)],
    )

    if summary_doc and summary_doc.get("title"):
        # Dùng minute-bucket của expires_at làm phần cache key
        summary_bucket = (
            summary_doc["expires_at"].strftime("%Y%m%d%H%M")
            if summary_doc.get("expires_at")
            else "x"
        )
        cache_key = f"audio:{slug}:{summary_bucket}"

        # ── Check audio cache với key gắn theo summary ────────────────────────
        cached = audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}})
        if cached and cached.get("audio_b64"):
            audio_bytes = base64.b64decode(cached["audio_b64"])
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={"Cache-Control": "public, max-age=7200", "Content-Length": str(len(audio_bytes))},
            )

        title = summary_doc.get("title", "")
        lead = summary_doc.get("lead", "")
        body_paras = summary_doc.get("body") or []
        conclusion = summary_doc.get("conclusion", "")
        key_points = summary_doc.get("key_points") or []

        parts = []
        if title:
            parts.append(title)
        if lead:
            parts.append(lead)
        if body_paras:
            parts.extend(body_paras)
        if conclusion:
            parts.append(conclusion)
        if key_points:
            parts.append("Các điểm chính: " + ". ".join(key_points))
        tts_text = ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())
    else:
        # ── Fallback: lấy headline từ hotnews_v2_cache nếu chưa có summary ──
        cache_key = f"audio:{slug}:fallback"
        cached = audio_cache.find_one({"key": cache_key, "expires_at": {"$gt": now}})
        if cached and cached.get("audio_b64"):
            audio_bytes = base64.b64decode(cached["audio_b64"])
            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type="audio/mpeg",
                headers={"Cache-Control": "public, max-age=7200", "Content-Length": str(len(audio_bytes))},
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
            raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu cho chủ đề này. Hãy xem tóm tắt AI trước.")
        tts_text = cluster_doc.get("name", slug) + ". " + (cluster_doc.get("headline") or "")

    # Giới hạn độ dài (edge-tts xử lý ổn đến ~7000 chars)
    if len(tts_text) > 7000:
        tts_text = tts_text[:7000]

    # ── Generate TTS ──────────────────────────────────────────────────────────
    try:
        audio_bytes = await _generate_tts_bytes(tts_text)
    except Exception as exc:
        logger.error(f"TTS generation failed for slug={slug}: {exc}")
        raise HTTPException(status_code=503, detail=f"Không thể tạo audio: {exc}")

    if not audio_bytes:
        raise HTTPException(status_code=503, detail="edge-tts trả về dữ liệu trống.")

    # ── Lưu cache (TTL 2h) ───────────────────────────────────────────────────
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
        headers={"Cache-Control": "public, max-age=7200", "Content-Length": str(len(audio_bytes))},
    )


# =============================================================================
# Admin: ML Model Metrics
# =============================================================================

@app.get("/admin/ml-metrics", tags=["Admin"])
async def get_ml_metrics(current_user: str = Depends(get_current_admin_user)):
    """Trả về báo cáo đánh giá mô hình ML từ file evaluation_report.json."""
    import json as _json
    report_path = Path("models") / "evaluation_report.json"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Chưa có báo cáo đánh giá. Hãy chạy scripts/evaluate_model.py trước."
        )
    try:
        with open(report_path, encoding="utf-8") as f:
            report = _json.load(f)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể đọc file báo cáo: {exc}")


# =============================================================================
# Admin: Hot Topics Management
# =============================================================================

@app.delete("/admin/hotnews-cache", tags=["Admin"])
async def clear_hotnews_cache(current_user: str = Depends(get_current_admin_user)):
    """Force-clear hotnews_v2_cache + hotnews_summary_cache + hotnews_audio_cache so all windows recompute fresh."""
    global _hotnews_mem
    _hotnews_mem.clear()
    db = get_db()
    r1 = db["hotnews_v2_cache"].delete_many({})
    r2 = db["hotnews_summary_cache"].delete_many({})
    r3 = db["hotnews_audio_cache"].delete_many({})
    return {
        "deleted_clusters": r1.deleted_count,
        "deleted_summaries": r2.deleted_count,
        "deleted_audio": r3.deleted_count,
        "message": "All caches cleared. Next request will recompute.",
    }


@app.delete("/admin/hotnews-audio-cache/{slug}", tags=["Admin"])
async def clear_audio_cache_for_slug(slug: str, current_user: str = Depends(get_current_admin_user)):
    """Xóa audio cache của một slug cụ thể (để force re-generate với nội dung mới nhất)."""
    db = get_db()
    r = db["hotnews_audio_cache"].delete_many({"key": re.compile(f"^audio:{re.escape(slug)}")})
    return {"deleted": r.deleted_count, "slug": slug, "message": f"Đã xóa {r.deleted_count} audio cache entries cho '{slug}'."}


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
    return await check_openai_status()


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

    suggestions = await detect_new_hot_topics(
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
    expanded = await expand_keywords(topic["name"], original_keywords)

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


@app.post("/settings/change-password", tags=["Settings"])
async def change_password(
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Change user password."""
    from src.api.auth import authenticate_user, get_password_hash, verify_password

    current_password = request.get("current_password")
    new_password = request.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    if not authenticate_user(current_user, current_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải từ 6 ký tự trở lên.")

    users_col = get_users_collection()
    result = users_col.update_one(
        {"username": current_user},
        {"$set": {"password_hash": get_password_hash(new_password)}}
    )
    if result.matched_count == 0:
        # env-var admin – cannot change via DB
        raise HTTPException(status_code=400, detail="Tài khoản admin env không thể đổi mật khẩu qua đây.")

    logger.info(f"Password changed for {current_user}")
    return {"message": "Đổi mật khẩu thành công."}


# =============================================================================
# Admin: User Management
# =============================================================================

@app.get("/admin/users", tags=["Admin - Users"])
async def admin_list_users(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: active|banned|pending"),
    role: Optional[str] = Query(None, description="Lọc theo vai trò: user|admin"),
    q: Optional[str] = Query(None, description="Tìm theo username hoặc email"),
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
    docs = list(users_col.find(query, {"password_hash": 0, "_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    return {"users": docs, "total": total, "skip": skip, "limit": limit}


@app.get("/admin/users/stats/summary", tags=["Admin - Users"])
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
    by_status = {}
    by_role = {}
    for r in rows:
        s = r["_id"]["status"]
        rl = r["_id"]["role"]
        by_status[s] = by_status.get(s, 0) + r["count"]
        by_role[rl] = by_role.get(rl, 0) + r["count"]
    return {"total": total, "by_status": by_status, "by_role": by_role}


@app.get("/admin/users/{username}", tags=["Admin - Users"])
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


@app.put("/admin/users/{username}/status", tags=["Admin - Users"])
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


@app.put("/admin/users/{username}/role", tags=["Admin - Users"])
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


@app.delete("/admin/users/{username}", tags=["Admin - Users"])
async def admin_delete_user(
    username: str,
    current_user: str = Depends(get_current_admin_user),
):
    """Admin: Xóa tài khoản user và toàn bộ dữ liệu liên quan."""
    if username == current_user:
        raise HTTPException(status_code=400, detail="Không thể tự xóa tài khoản của mình.")
    users_col = get_users_collection()

    # Lấy _id trước để xoá user_channels (keyed by user_id)
    user_doc = users_col.find_one({"username": username}, {"_id": 1})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_id_str = str(user_doc["_id"])
    db = get_db()

    # Xóa user khỏi users collection
    users_col.delete_one({"_id": user_doc["_id"]})

    # Dọn dẹp toàn bộ dữ liệu liên quan để re-test sạch
    db["user_channels"].delete_many({"user_id": user_id_str})
    db["notifications"].delete_many({"user": username})
    db["user_settings"].delete_many({"username": username})

    logger.info(f"Admin {current_user} deleted user {username} (id={user_id_str}) + related data")
    return {"success": True}

