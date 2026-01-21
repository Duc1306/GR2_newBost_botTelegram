"""Check sources in database."""
from src.db.mongo import get_db

db = get_db()

total = db.posts.count_documents({})
telegram_generic = db.posts.count_documents({'source': 'telegram'})
sources = list(db.posts.distinct('source'))

print(f"Total posts: {total}")
print(f"Posts with generic 'telegram' source: {telegram_generic}")
print(f"\nAll sources ({len(sources)}):")
for src in sorted(sources):
    count = db.posts.count_documents({'source': src})
    print(f"  {src}: {count}")
