"""
Quick script to check labeled data in MongoDB.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_db

def main():
    print("=" * 60)
    print("Checking Database Labels")
    print("=" * 60)
    
    db = get_db()
    collection = db["posts"]
    
    # Total posts
    total = collection.count_documents({})
    print(f"\n📊 Total posts in DB: {total:,}")
    
    # Posts with topics field
    with_topics = collection.count_documents({"topics": {"$exists": True}})
    print(f"📌 Posts with topics field: {with_topics:,}")
    
    # Posts with non-empty topics
    with_labels = collection.count_documents({"topics": {"$exists": True, "$ne": []}})
    print(f"✅ Posts with labels (non-empty topics): {with_labels:,}")
    
    if with_labels > 0:
        # Sample post
        print("\n" + "=" * 60)
        print("Sample Post:")
        print("=" * 60)
        sample = collection.find_one({"topics": {"$exists": True, "$ne": []}})
        print(f"ID: {sample.get('id')}")
        print(f"Topics: {sample.get('topics')}")
        print(f"Text preview: {sample.get('text', '')[:200]}...")
        
        # Topic distribution
        print("\n" + "=" * 60)
        print("Topic Distribution:")
        print("=" * 60)
        pipeline = [
            {"$match": {"topics": {"$exists": True, "$ne": []}}},
            {"$unwind": "$topics"},
            {"$group": {"_id": "$topics", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        for result in collection.aggregate(pipeline):
            print(f"  {result['_id']}: {result['count']:,}")
    else:
        print("\n⚠️ No labeled data found!")
        print("\n💡 Run rule-based classifier first:")
        print("   scripts\\fetch_telegram.cmd full")

if __name__ == "__main__":
    main()
