"""Re-classify posts using CHANNEL CATEGORY first, then content-based ML
Priority: Channel category > Content-based ML classification
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_posts_collection, get_db
from src.processing.topic_classifier import TopicClassifier
import argparse

def reclassify_with_channel_categories(limit: int = None, dry_run: bool = True):
    """Re-classify posts using channel categories"""
    posts_coll = get_posts_collection()
    db = get_db()
    channels_coll = db['channel_metadata']
    classifier = TopicClassifier()
    
    # Build channel -> category mapping
    print("📊 Building channel → category mapping...")
    channel_category_map = {}
    for ch in channels_coll.find({"category": {"$exists": True, "$ne": None}}):
        username = ch.get('username')
        category = ch.get('category')
        if username and category:
            channel_category_map[username] = category
    
    print(f"   ✅ Loaded {len(channel_category_map)} channels with categories")
    
    # Find all posts
    query = {}
    total = posts_coll.count_documents(query)
    
    print("\n" + "=" * 60)
    print("🔄 RE-CLASSIFY WITH CHANNEL CATEGORIES")
    print("=" * 60)
    print(f"\n📊 Total posts to process: {total:,}")
    
    if limit:
        print(f"   Limiting to: {limit:,} posts")
        cursor = posts_coll.find(query).limit(limit)
    else:
        cursor = posts_coll.find(query)
    
    if dry_run:
        print("\n⚠️ DRY RUN MODE - No changes will be saved!")
    else:
        print("\n✅ APPLY MODE - Changes will be saved to database!")
    
    print()
    
    processed = 0
    updated_by_channel = 0
    updated_by_ml = 0
    skipped = 0
    errors = 0
    
    for post in cursor:
        processed += 1
        
        if processed % 1000 == 0:
            print(f"   Processed: {processed:,}/{total:,} ({processed/total*100:.1f}%)")
        
        try:
            source = post.get('source', '')
            text = post.get('text', '') or post.get('text_cleaned', '')
            lang = post.get('lang', 'vi')
            
            # Try channel category first
            channel_category = None
            if source in channel_category_map:
                channel_category = channel_category_map[source]
            
            if channel_category:
                # Use channel category
                topics = [channel_category]
                classification_method = "channel"
            else:
                # Fall back to ML classification
                if not text or len(text) < 10:
                    skipped += 1
                    continue
                
                topics = classifier.classify(text, lang)
                if not topics:
                    topics = []
                classification_method = "ml"
            
            # Update if different
            old_topics = post.get('topics', [])
            if set(topics) != set(old_topics):
                if dry_run:
                    if (updated_by_channel + updated_by_ml) < 20:  # Show first 20
                        print(f"\n   Would update: {source}")
                        print(f"      Method: {classification_method}")
                        print(f"      Old: {old_topics}")
                        print(f"      New: {topics}")
                else:
                    posts_coll.update_one(
                        {"_id": post["_id"]},
                        {"$set": {"topics": topics}}
                    )
                
                if classification_method == "channel":
                    updated_by_channel += 1
                else:
                    updated_by_ml += 1
        
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"   ❌ Error processing post {post.get('_id')}: {e}")
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Processed: {processed:,}")
    print(f"✅ Updated by channel category: {updated_by_channel:,}")
    print(f"✅ Updated by ML: {updated_by_ml:,}")
    print(f"⚠️ Skipped: {skipped:,}")
    print(f"❌ Errors: {errors:,}")
    
    if dry_run:
        print("\n⚠️ This was a DRY RUN. To apply changes, run:")
        print("   python scripts/reclassify_with_channel_categories.py --apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-classify posts using channel categories")
    parser.add_argument("--limit", type=int, help="Limit number of posts to process")
    parser.add_argument("--apply", action="store_true", help="Apply changes (not dry run)")
    
    args = parser.parse_args()
    
    reclassify_with_channel_categories(
        limit=args.limit,
        dry_run=not args.apply
    )
