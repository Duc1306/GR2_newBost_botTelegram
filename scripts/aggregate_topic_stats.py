"""
Aggregate Topic Statistics - Daily topic stats for dashboard
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db


def aggregate_topic_stats_for_date(date: datetime, platform: str = "all"):
    """
    Aggregate topic stats for a specific date.
    
    Args:
        date: Date to aggregate (start of day UTC)
        platform: "telegram" | "twitter" | "all"
    """
    db = get_db()
    posts = db["posts"]
    topic_stats = db["topic_stats"]
    
    # Date range (full day)
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    # Build query
    query = {
        "created_at": {"$gte": start_date, "$lt": end_date},
        "topic_predictions": {"$exists": True, "$ne": []}
    }
    
    if platform != "all":
        query["platform"] = platform
    
    # Fetch posts
    cursor = posts.find(query)
    
    # Aggregate by topic
    topic_data = defaultdict(lambda: {
        "posts": [],
        "confidences": [],
        "scores": [],
        "sources": Counter(),
        "keywords": Counter()
    })
    
    for post in cursor:
        # Get primary topic (highest confidence)
        predictions = post.get("topic_predictions", [])
        if not predictions:
            continue
        
        primary_pred = max(predictions, key=lambda p: p.get("confidence", 0))
        topic = primary_pred.get("topic")
        confidence = primary_pred.get("confidence", 0)
        
        if not topic:
            continue
        
        # Aggregate metrics
        topic_data[topic]["posts"].append(post["_id"])
        topic_data[topic]["confidences"].append(confidence)
        topic_data[topic]["scores"].append(post.get("score", 0))
        topic_data[topic]["sources"][post.get("source", "unknown")] += 1
        
        # Extract keywords (simple: split by space, take top words)
        text = post.get("text_cleaned") or post.get("text", "")
        words = [w.lower() for w in text.split() if len(w) > 3]
        topic_data[topic]["keywords"].update(words[:20])  # Top 20 words per post
    
    # Save stats for each topic
    for topic, data in topic_data.items():
        post_count = len(data["posts"])
        
        if post_count == 0:
            continue
        
        avg_confidence = sum(data["confidences"]) / post_count
        avg_score = sum(data["scores"]) / post_count
        
        # Top 10 keywords
        top_keywords = [
            {"keyword": word, "count": count}
            for word, count in data["keywords"].most_common(10)
        ]
        
        # Top 5 sources
        top_sources = [
            {"source": source, "count": count}
            for source, count in data["sources"].most_common(5)
        ]
        
        # Calculate trend (compare with yesterday)
        yesterday = start_date - timedelta(days=1)
        yesterday_stats = topic_stats.find_one({
            "topic": topic,
            "date": yesterday,
            "platform": platform
        })
        
        if yesterday_stats:
            yesterday_count = yesterday_stats.get("post_count", 1)
            trend_score = post_count / yesterday_count
            
            if trend_score > 1.2:
                trend_direction = "up"
            elif trend_score < 0.8:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            trend_score = 1.0
            trend_direction = "stable"
        
        # Upsert stats
        stat_doc = {
            "topic": topic,
            "date": start_date,
            "platform": platform,
            "post_count": post_count,
            "avg_confidence": round(avg_confidence, 3),
            "avg_score": round(avg_score, 2),
            "top_keywords": top_keywords,
            "trend_score": round(trend_score, 2),
            "trend_direction": trend_direction,
            "top_sources": top_sources,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        topic_stats.update_one(
            {"topic": topic, "date": start_date, "platform": platform},
            {"$set": stat_doc},
            upsert=True
        )
        
        print(f"  {topic:15} | {post_count:4} posts | conf: {avg_confidence:.2f} | trend: {trend_score:.2f}x {trend_direction}")


def aggregate_last_n_days(days: int = 7):
    """Aggregate stats for last N days."""
    print("=" * 60)
    print(f"Aggregating Topic Stats - Last {days} Days")
    print("=" * 60)
    
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(days):
        date = today - timedelta(days=i)
        print(f"\ {date.strftime('%Y-%m-%d')}:")
        
        # Aggregate for "all" platforms
        aggregate_topic_stats_for_date(date, platform="all")
    
    print("\ Aggregation completed!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate topic statistics")
    parser.add_argument("--days", type=int, default=7, help="Number of days to aggregate (default: 7)")
    parser.add_argument("--date", type=str, help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--platform", type=str, default="all", choices=["telegram", "twitter", "all"])
    
    args = parser.parse_args()
    
    if args.date:
        # Aggregate specific date
        date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=UTC)
        print(f"Aggregating stats for {args.date}...")
        aggregate_topic_stats_for_date(date, platform=args.platform)
    else:
        # Aggregate last N days
        aggregate_last_n_days(args.days)


if __name__ == "__main__":
    main()
