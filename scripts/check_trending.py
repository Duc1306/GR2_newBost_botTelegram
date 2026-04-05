from src.db.mongo import get_db
from datetime import datetime, timedelta

db = get_db()
posts = db['posts']
since = datetime.utcnow() - timedelta(hours=72)
pipeline = [
    {"$match": {"created_at": {"$gte": since}, "topics": {"$exists": True, "$ne": []}}},
    {"$unwind": "$topics"},
    {"$group": {
        "_id": "$topics",
        "count": {"$sum": 1},
        "latest": {"$max": "$created_at"},
        "with_links": {"$sum": {"$cond": [{"$gt": [{"$size": {"$ifNull": ["$links", []]}}, 0]}, 1, 0]}}
    }},
    {"$sort": {"count": -1}},
    {"$limit": 15}
]
results = list(posts.aggregate(pipeline))
for r in results:
    print(f'{str(r["_id"]):40s}  count={r["count"]:4d}  with_links={r["with_links"]:4d}')

# Also check a sample post structure
print("\n--- Sample post ---")
p = posts.find_one({"created_at": {"$gte": since}, "topics": {"$exists": True}})
if p:
    print("topics:", p.get("topics"))
    print("links:", p.get("links"))
    print("text:", (p.get("text") or "")[:100])
