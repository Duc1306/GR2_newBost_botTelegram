from src.db.mongo import get_db
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db = get_db()
since = datetime.utcnow() - timedelta(hours=72)

print("=== SOURCES ===")
for s in db.sources.find({}, {'username':1,'name':1,'category':1,'_id':0}):
    print(" ", s)

print("\n=== CHANNEL METADATA (top 15) ===")
for c in db.channel_metadata.find({}, {'username':1,'category':1,'_id':0}).limit(15):
    print(" ", c.get('username'), '|', c.get('category'))

print("\n=== POSTS BY CHANNEL (top 15, last 72h) ===")
from pymongo import MongoClient
pipeline = [
    {"$match": {"created_at": {"$gte": since}}},
    {"$group": {"_id": "$channel_username", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 15}
]
for r in db.posts.aggregate(pipeline):
    print(f"  {str(r['_id']):35s}  {r['count']} posts")

print("\n=== TRENDING TOPICS (72h) ===")
pipeline2 = [
    {"$match": {"created_at": {"$gte": since}, "topics": {"$exists": True, "$ne": []}}},
    {"$unwind": "$topics"},
    {"$group": {"_id": "$topics", "count": {"$sum": 1}, "with_links": {"$sum": {"$cond": [{"$gt": [{"$size": {"$ifNull": ["$links", []]}}, 0]}, 1, 0]}}}},
    {"$sort": {"count": -1}},
    {"$limit": 15}
]
for r in db.posts.aggregate(pipeline2):
    print(f"  {str(r['_id']):40s}  count={r['count']:4d}  links={r['with_links']}")
