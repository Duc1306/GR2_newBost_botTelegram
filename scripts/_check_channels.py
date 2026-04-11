import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.db.mongo import get_db, init_mongo
init_mongo()
get_db_sync = get_db

db = get_db_sync()
print("Collections:", db.list_collection_names())
channels = db["channels"]

total = channels.count_documents({})
active = channels.count_documents({"status": "active"})

print("total channels:", total)
print("active channels:", active)

statuses = list(channels.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}]))
print("status dist:", statuses)

platforms = list(channels.aggregate([{"$group": {"_id": "$platform", "count": {"$sum": 1}}}]))
print("platform dist:", platforms)

sample = list(channels.find({}, {"status": 1, "platform": 1, "title": 1, "_id": 0}).limit(3))
print("sample docs:", sample)

# Check channel_metadata (where 108 telegram channels actually live)
meta = db["channel_metadata"]
print("\n--- channel_metadata ---")
print("total:", meta.count_documents({}))
statuses_meta = list(meta.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}]))
print("status dist:", statuses_meta)
plat_meta = list(meta.aggregate([{"$group": {"_id": "$platform", "count": {"$sum": 1}}}]))
print("platform dist:", plat_meta)
sample2 = list(meta.find({}, {"status": 1, "platform": 1, "username": 1, "_id": 0}).limit(3))
print("sample:", sample2)
