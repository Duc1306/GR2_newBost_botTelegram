"""
Extract Keyword Trends - Daily keyword frequency tracking
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC
from collections import Counter, defaultdict
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db


# Vietnamese + English stopwords — expanded to remove noise from news text
STOPWORDS = {
    # ── Vietnamese structural words ──────────────────────────────────────────
    'và', 'của', 'có', 'được', 'trong', 'cho', 'từ', 'này', 'đã', 'là', 'với',
    'các', 'một', 'những', 'về', 'để', 'đến', 'trên', 'theo', 'như', 'khi',
    'mà', 'thì', 'sẽ', 'hay', 'cũng', 'đây', 'còn', 'rằng', 'bởi', 'nên',
    'hơn', 'đó', 'sau', 'vào', 'bị', 'vì', 'tại', 'tới', 'nếu', 'lại',
    'nữa', 'rất', 'quá', 'mọi', 'dù', 'tuy', 'nhưng', 'vẫn', 'cũng', 'thêm',
    'đang', 'đều', 'kể', 'gì', 'nào', 'đâu', 'sao', 'chứ', 'nhé', 'thôi',
    'ấy', 'đấy', 'thế', 'vậy', 'xin', 'hãy', 'đã', 'chưa', 'chỉ', 'mới',
    'cả', 'lên', 'xuống', 'ra', 'vào', 'qua', 'lại', 'đi', 'về', 'lên',
    # ── News-domain noise (appear in every article) ──────────────────────────
    'tin', 'bài', 'mới', 'nhất', 'via', 'rss', 'nội', 'dung', 'thông',
    'theo', 'nguồn', 'ảnh', 'video', 'xem', 'đọc', 'tiếp', 'more', 'read',
    'click', 'link', 'http', 'https', 'www', 'com', 'net', 'org', 'vn',
    # ── News source names (not meaningful keywords) ──────────────────────────
    'vnexpress', 'tuoitre', 'dantri', 'vtv', 'vov', 'zing', 'zingnews',
    'cafef', 'kenh14', 'thanhnien', 'nguoiduatin', 'baomoi', 'nld', 'laodong',
    'tienphong', 'plo', 'soha', 'eva', 'afamily', 'vietnamnet', 'vietcong',
    'vnpt', 'viettel', 'mobifone', 'thethaovanhoa', 'bongda', 'saostar',
    # ── English structural words ─────────────────────────────────────────────
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
    'has', 'have', 'had', 'been', 'not', 'this', 'that', 'it', 'its',
    'he', 'she', 'they', 'we', 'you', 'i', 'his', 'her', 'their', 'our',
    'will', 'can', 'may', 'also', 'more', 'new', 'top', 'all', 'get',
    # ── Number-like tokens ───────────────────────────────────────────────────
    '000', '0000', '00000',
}


def extract_keywords(text: str, min_length: int = 3) -> list:
    """Extract keywords from text."""
    if not text:
        return []
    
    # Lowercase and split
    text = text.lower()
    
    # Keep only alphanumeric and Vietnamese characters
    words = re.findall(r'[a-zA-Z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+', text)
    
    # Filter stopwords, short words, and pure-numeric tokens
    keywords = [
        w for w in words
        if len(w) >= min_length
        and w not in STOPWORDS
        and not re.match(r'^\d+$', w)          # skip pure numbers (000, 2024, etc.)
        and not re.match(r'^[0-9,\.]+$', w)    # skip number-like tokens (1.000, 50,000)
    ]
    
    return keywords


def extract_keyword_trends_for_date(date: datetime):
    """
    Extract keyword trends for a specific date.
    
    Args:
        date: Date to process (start of day UTC)
    """
    db = get_db()
    posts = db["posts"]
    keyword_trends = db["keyword_trends"]
    
    # Date range (full day)
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    # Fetch posts
    query = {
        "created_at": {"$gte": start_date, "$lt": end_date}
    }
    cursor = posts.find(query)
    
    # Aggregate keywords
    keyword_data = defaultdict(lambda: {
        "platforms": Counter(),
        "topics": Counter(),
        "posts": set()
    })
    
    for post in cursor:
        platform = post.get("platform", "telegram")
        text = post.get("text_cleaned") or post.get("text", "")
        
        # Get primary topic
        primary_topic = None
        predictions = post.get("topic_predictions", [])
        if predictions:
            primary_pred = max(predictions, key=lambda p: p.get("confidence", 0))
            primary_topic = primary_pred.get("topic")
        
        # Extract keywords
        keywords = extract_keywords(text)
        
        for keyword in keywords:
            keyword_normalized = keyword.lower()
            keyword_data[keyword_normalized]["platforms"][platform] += 1
            keyword_data[keyword_normalized]["posts"].add(str(post["_id"]))
            
            if primary_topic:
                keyword_data[keyword_normalized]["topics"][primary_topic] += 1
    
    # Save top keywords only (to avoid DB bloat)
    # Top 500 keywords by frequency
    sorted_keywords = sorted(
        keyword_data.items(),
        key=lambda x: sum(x[1]["platforms"].values()),
        reverse=True
    )[:500]
    
    saved_count = 0
    
    for keyword_normalized, data in sorted_keywords:
        platforms_dict = dict(data["platforms"])
        topics_dict = dict(data["topics"])
        total_count = sum(platforms_dict.values())
        unique_posts = len(data["posts"])
        
        # Calculate trend velocity (compare with yesterday)
        yesterday = start_date - timedelta(days=1)
        yesterday_trend = keyword_trends.find_one({
            "keyword_normalized": keyword_normalized,
            "date": yesterday
        })
        
        if yesterday_trend:
            yesterday_count = yesterday_trend.get("total_count", 1)
            change_from_yesterday = total_count - yesterday_count
            change_pct = (total_count - yesterday_count) / yesterday_count
            
            # Calculate trend velocity (7-day average)
            week_ago = start_date - timedelta(days=7)
            week_trends = list(keyword_trends.find({
                "keyword_normalized": keyword_normalized,
                "date": {"$gte": week_ago, "$lt": start_date}
            }))
            
            if week_trends:
                avg_count = sum(t.get("total_count", 0) for t in week_trends) / len(week_trends)
                trend_velocity = total_count / avg_count if avg_count > 0 else 1.0
            else:
                trend_velocity = 1.0
        else:
            change_from_yesterday = total_count
            change_pct = 0.0
            trend_velocity = 1.0
        
        # Find related keywords (co-occurrence)
        # TODO: Implement co-occurrence analysis
        related_keywords = []
        
        # Upsert trend
        trend_doc = {
            "keyword": keyword_normalized,
            "keyword_normalized": keyword_normalized,
            "date": start_date,
            "platforms": {
                "telegram": platforms_dict.get("telegram", 0),
                "twitter": platforms_dict.get("twitter", 0),
                "total": total_count
            },
            "topics": topics_dict,
            "total_count": total_count,
            "unique_posts": unique_posts,
            "trend_velocity": round(trend_velocity, 2),
            "change_from_yesterday": change_from_yesterday,
            "change_pct": round(change_pct, 3),
            "related_keywords": related_keywords,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        
        keyword_trends.update_one(
            {"keyword_normalized": keyword_normalized, "date": start_date},
            {"$set": trend_doc},
            upsert=True
        )
        
        saved_count += 1
        
        if saved_count <= 20:  # Show top 20
            print(f"  {keyword_normalized:20} | {total_count:4}x | trend: {trend_velocity:.2f}x")
    
    print(f"\n  Saved {saved_count} keywords")


def extract_last_n_days(days: int = 7):
    """Extract keyword trends for last N days."""
    print("=" * 60)
    print(f"Extracting Keyword Trends - Last {days} Days")
    print("=" * 60)
    
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(days):
        date = today - timedelta(days=i)
        print(f"\n {date.strftime('%Y-%m-%d')}:")
        extract_keyword_trends_for_date(date)
    
    print("\n Extraction completed!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract keyword trends")
    parser.add_argument("--days", type=int, default=7, help="Number of days to process (default: 7)")
    parser.add_argument("--date", type=str, help="Specific date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.date:
        # Extract specific date
        date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=UTC)
        print(f"Extracting keywords for {args.date}...")
        extract_keyword_trends_for_date(date)
    else:
        # Extract last N days
        extract_last_n_days(args.days)


if __name__ == "__main__":
    main()
