"""Check recent posts topics."""
from src.db.mongo import get_db
from datetime import datetime, timedelta

db = get_db()

# Posts trong 1 giờ gần nhất
one_hour_ago = datetime.now() - timedelta(hours=1)

recent_posts = list(db.posts.find({
    'created_at': {'$gte': one_hour_ago}
}).sort('created_at', -1).limit(10))

print(f"Recent posts (last 1 hour): {len(recent_posts)}\n")

for p in recent_posts:
    print(f"Source: {p.get('source', 'N/A')}")
    print(f"Topics: {p.get('topics', [])}")
    print(f"Text: {p.get('text', '')[:80]}...")
    print(f"Score: {p.get('score', 0)}")
    print("-" * 80)

# Statistics
total = db.posts.count_documents({})
with_topics = db.posts.count_documents({'topics': {'$exists': True, '$ne': []}})
without_topics = total - with_topics

print(f"\nTotal posts: {total}")
print(f"With topics: {with_topics} ({with_topics/total*100:.1f}%)")
print(f"Without topics: {without_topics} ({without_topics/total*100:.1f}%)")
