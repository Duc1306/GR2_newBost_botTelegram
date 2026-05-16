"""Analytics routes: trends, keywords, timeline, comparison, heatmap."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from src.db.mongo import get_db

router = APIRouter(tags=["Analytics"])


@router.get("/topics/trending")
async def get_trending_topics(
    days: int = Query(7, ge=1, le=90),
    platform: Optional[str] = Query("all"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get trending topics (rising in popularity)."""
    db = get_db()
    posts = db["posts"]

    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    mid_date = end_date - timedelta(days=days // 2)

    platform_filter = {} if platform == "all" else {"platform": platform}

    facet_result = list(posts.aggregate([
        {"$match": {
            "created_at": {"$gte": start_date, "$lt": end_date},
            "topics": {"$exists": True, "$ne": []},
            **platform_filter,
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
        }},
    ]))
    facet = facet_result[0] if facet_result else {}

    recent_by_topic = {s["_id"]: s["count"] for s in facet.get("recent", [])}
    previous_by_topic = {s["_id"]: s["count"] for s in facet.get("previous", [])}

    trends = []
    for topic, current_count in recent_by_topic.items():
        previous_count = previous_by_topic.get(topic, 0)
        if previous_count > 0:
            growth_percentage = ((current_count - previous_count) / previous_count) * 100
            trend_score = current_count / previous_count
        else:
            growth_percentage = 100.0
            trend_score = float("inf")

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
            "trend_score": round(trend_score, 2) if trend_score != float("inf") else 999,
        })

    trends.sort(key=lambda x: x["current_count"], reverse=True)
    return {
        "data": trends[:limit],
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "days": days,
        },
    }


@router.get("/analytics/keywords")
async def get_keywords(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    topic: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    min_count: int = Query(5, ge=1),
):
    """Get top keywords by frequency."""
    db = get_db()
    keyword_trends = db["keyword_trends"]

    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    query = {
        "date": {"$gte": start_date, "$lte": end_date},
        "total_count": {"$gte": min_count},
    }

    cursor = keyword_trends.find(query).sort("total_count", -1).limit(limit * 2)
    keywords_data = list(cursor)

    keywords_agg: dict = {}
    for kw_doc in keywords_data:
        kw = kw_doc["keyword"]
        if kw not in keywords_agg:
            keywords_agg[kw] = {
                "count": 0, "unique_posts": 0,
                "platforms": {"telegram": 0, "twitter": 0},
                "topics": {}, "trend_velocities": [],
            }
        keywords_agg[kw]["count"] += kw_doc.get("total_count", 0)
        keywords_agg[kw]["unique_posts"] += kw_doc.get("unique_posts", 0)
        platforms_data = kw_doc.get("platforms", {})
        keywords_agg[kw]["platforms"]["telegram"] += platforms_data.get("telegram", 0)
        keywords_agg[kw]["platforms"]["twitter"] += platforms_data.get("twitter", 0)
        for t, cnt in kw_doc.get("topics", {}).items():
            if topic is None or t == topic:
                keywords_agg[kw]["topics"][t] = keywords_agg[kw]["topics"].get(t, 0) + cnt
        if "trend_velocity" in kw_doc:
            keywords_agg[kw]["trend_velocities"].append(kw_doc["trend_velocity"])

    if topic:
        keywords_agg = {k: v for k, v in keywords_agg.items() if topic in v["topics"]}

    keywords_result = []
    for kw, data in keywords_agg.items():
        avg_velocity = (
            sum(data["trend_velocities"]) / len(data["trend_velocities"])
            if data["trend_velocities"] else 1.0
        )
        keywords_result.append({
            "keyword": kw,
            "count": data["count"],
            "unique_posts": data["unique_posts"],
            "platforms": data["platforms"],
            "topics": data["topics"],
            "trend_velocity": round(avg_velocity, 2),
        })

    keywords_result.sort(key=lambda x: x["count"], reverse=True)
    return {
        "keywords": keywords_result[:limit],
        "total": len(keywords_result),
        "period": {"from": date_from, "to": date_to},
    }


@router.get("/analytics/keywords/trending")
async def get_trending_keywords(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=100),
    min_velocity: float = Query(1.5, ge=1.0),
):
    """Get trending keywords (fastest growing)."""
    db = get_db()
    keyword_trends = db["keyword_trends"]

    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)

    cursor = keyword_trends.find({
        "date": {"$gte": start_date, "$lt": end_date},
        "trend_velocity": {"$gte": min_velocity},
    }).sort("trend_velocity", -1)
    keywords_data = list(cursor)

    keywords_agg: dict = {}
    for kw_doc in keywords_data:
        kw = kw_doc["keyword"]
        if kw not in keywords_agg:
            keywords_agg[kw] = {"total_count": 0, "velocities": [], "topics": set()}
        keywords_agg[kw]["total_count"] += kw_doc.get("total_count", 0)
        keywords_agg[kw]["velocities"].append(kw_doc.get("trend_velocity", 1.0))
        for topic in kw_doc.get("topics", {}).keys():
            keywords_agg[kw]["topics"].add(topic)

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
            "related_topics": list(data["topics"]),
        })

    trending_keywords.sort(key=lambda x: x["trend_velocity"], reverse=True)
    return {
        "keywords": trending_keywords[:limit],
        "period": {"from": start_date.isoformat(), "to": end_date.isoformat(), "days": days},
    }


@router.get("/analytics/timeline")
async def get_timeline(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    granularity: str = Query("day", regex="^(day|week)$"),
):
    """Get post volume timeline."""
    db = get_db()
    posts = db["posts"]

    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query: dict = {"created_at": {"$gte": start_date, "$lte": end_date}}
    if platform and platform != "all":
        query["platform"] = platform
    if topic:
        query["topic_predictions.topic"] = topic

    if granularity == "day":
        date_format = "%Y-%m-%d"
    else:
        date_format = "%Y-W%V"

    group_id = {"$dateToString": {"format": date_format, "date": "$created_at"}}

    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": group_id,
            "count": {"$sum": 1},
            "platforms": {"$push": "$platform"},
            "topics": {"$push": "$topics"},
        }},
        {"$sort": {"_id": 1}},
    ]
    results = list(posts.aggregate(pipeline))

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

        platforms_count: dict = {}
        for p in result["platforms"]:
            platforms_count[p] = platforms_count.get(p, 0) + 1

        topics_count: dict = {}
        for topics_list in result["topics"]:
            for t in topics_list:
                topics_count[t] = topics_count.get(t, 0) + 1

        timeline.append({
            "date": result["_id"],
            "count": count,
            "by_platform": platforms_count,
            "by_topic": topics_count,
        })

    avg_per_period = total_posts / len(timeline) if timeline else 0
    return {
        "timeline": timeline,
        "summary": {
            "total_posts": total_posts,
            "avg_per_period": round(avg_per_period, 1),
            "peak_date": peak_date,
            "peak_count": max_count,
        },
        "period": {"from": date_from, "to": date_to},
    }


@router.get("/analytics/comparison")
async def get_platform_comparison(
    date_from: str = Query(...),
    date_to: str = Query(...),
    metric: str = Query("volume", regex="^(volume|topics|keywords)$"),
):
    """Compare platforms (Telegram vs Twitter)."""
    db = get_db()
    posts = db["posts"]

    try:
        start_date = datetime.fromisoformat(date_from)
        end_date = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = {"created_at": {"$gte": start_date, "$lte": end_date}}
    days = (end_date - start_date).days + 1

    facet_result = list(posts.aggregate([
        {"$match": query},
        {"$facet": {
            "telegram_count": [
                {"$match": {"platform": "telegram"}}, {"$count": "n"},
            ],
            "telegram_topics": [
                {"$match": {"platform": "telegram", "topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 5},
            ],
            "twitter_count": [
                {"$match": {"platform": "twitter"}}, {"$count": "n"},
            ],
            "twitter_topics": [
                {"$match": {"platform": "twitter", "topics": {"$exists": True, "$ne": []}}},
                {"$unwind": "$topics"},
                {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 5},
            ],
        }},
    ]))
    f = facet_result[0] if facet_result else {}

    comparison = {}
    for plat in ["telegram", "twitter"]:
        total = (f.get(f"{plat}_count", [{}])[0] or {}).get("n", 0)
        top_topics = [{"topic": t["_id"], "count": t["count"]} for t in f.get(f"{plat}_topics", [])]
        comparison[plat] = {
            "total_posts": total,
            "avg_daily": round(total / days, 1) if days > 0 else 0,
            "top_topics": top_topics,
        }

    return {"comparison": comparison, "period": {"from": date_from, "to": date_to}}


@router.get("/analytics/heatmap")
async def get_activity_heatmap(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
):
    """Activity heatmap: số lượng bài theo giờ trong ngày và ngày trong tuần."""
    db = get_db()
    posts = db["posts"]

    to_date = datetime.fromisoformat(date_to) if date_to else datetime.utcnow()
    from_date = datetime.fromisoformat(date_from) if date_from else to_date - timedelta(days=30)

    query: dict = {"created_at": {"$gte": from_date, "$lte": to_date}}
    if topic:
        query["topics"] = topic

    pipeline = [
        {"$match": query},
        {"$project": {
            "hour": {"$hour": "$created_at"},
            "dayOfWeek": {"$dayOfWeek": "$created_at"},
        }},
        {"$group": {
            "_id": {"hour": "$hour", "dayOfWeek": "$dayOfWeek"},
            "count": {"$sum": 1},
        }},
    ]
    results = list(posts.aggregate(pipeline))

    heatmap: dict = {day: {hour: 0 for hour in range(24)} for day in range(7)}
    for item in results:
        dow = item["_id"]["dayOfWeek"]
        hour = item["_id"]["hour"]
        count = item["count"]
        day = 6 if dow == 1 else dow - 2
        heatmap[day][hour] = count

    return {
        "heatmap": heatmap,
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "total_posts": sum(sum(hours.values()) for hours in heatmap.values()),
    }
