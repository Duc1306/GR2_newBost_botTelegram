"""Check latest posts."""
from src.db.mongo import get_db

db = get_db()

latest_posts = list(db.posts.find().sort('_id', -1).limit(20))

print(f"Latest {len(latest_posts)} posts:\n")

for i, p in enumerate(latest_posts, 1):
    print(f"{i}. Source: {p.get('source', 'N/A')}")
    print(f"   Created: {p.get('created_at')}")
    print(f"   Topics: {p.get('topics', [])} (score: {p.get('score', 0):.2f})")
    print(f"   Text: {p.get('text', '')[:100]}...")
    if p.get('links'):
        print(f"   Links: {len(p['links'])} link(s)")
    if p.get('media'):
        media_types = [m.get('type', 'unknown') for m in p['media']]
        print(f"   Media: {media_types}")
    print()
