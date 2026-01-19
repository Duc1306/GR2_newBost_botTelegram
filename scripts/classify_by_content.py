#!/usr/bin/env python
"""
Classify ALL posts by their TEXT CONTENT using TopicClassifier.
This works for posts even without URLs or with non-news URLs (YouTube, Telegram, etc.)
"""

import sys
import argparse
from typing import Optional
from pymongo import UpdateOne

# Add parent directory to path
sys.path.append('.')

from src.db.mongo import get_posts_collection
from src.processing.topic_classifier import TopicClassifier


def classify_by_content(
    limit: Optional[int] = None,
    dry_run: bool = True,
    batch_size: int = 100
):
    """
    Classify posts by their text content using keyword-based TopicClassifier.
    
    Args:
        limit: Maximum number of posts to process (None = all)
        dry_run: If True, don't save to database
        batch_size: Number of updates to batch together
    """
    coll = get_posts_collection()
    classifier = TopicClassifier()
    
    # Find posts without source_topic
    query = {"source_topic": None, "text": {"$exists": True, "$ne": ""}}
    total_posts = coll.count_documents(query)
    
    print(f"\n📊 Tìm thấy {total_posts:,} posts có text chưa có source_topic")
    
    if dry_run:
        print("⚠️  CHẾ ĐỘ DRY RUN - Không lưu vào database\n")
    else:
        print("✅ CHẾ ĐỘ APPLY - Sẽ lưu vào database\n")
    
    # Process posts
    processed = 0
    success = 0
    failed = 0
    batch_updates = []
    topic_counts = {}
    
    cursor = coll.find(query).limit(limit) if limit else coll.find(query)
    
    for doc in cursor:
        processed += 1
        
        if processed % 100 == 0:
            print(f"\n📊 Progress: {processed:,}/{limit or total_posts:,} | Success: {success:,} | Failed: {failed:,}")
            if topic_counts:
                print(f"   Topic distribution: {topic_counts}\n")
        
        text = doc.get("text", "")
        if not text or len(text) < 10:  # Lowered from 20 to 10 chars
            failed += 1
            continue
        
        try:
            # Classify by content
            topics = classifier.classify(text)
            
            if topics and len(topics) > 0:
                source_topic = topics[0]  # Take first/main topic
                success += 1
                topic_counts[source_topic] = topic_counts.get(source_topic, 0) + 1
                
                old_topics = doc.get("topics", [])
                old_topic = old_topics[0] if old_topics else "(none)"
                
                if processed % 50 == 0:  # Show sample every 50
                    print(f"[{processed}] Text: {text[:60]}...")
                    print(f"  ✅ Topics: {topics}")
                    if old_topic != source_topic:
                        print(f"     OLD: {old_topic} | NEW: {source_topic}")
                
                if not dry_run:
                    batch_updates.append(
                        UpdateOne(
                            {"id": doc["id"]},
                            {"$set": {
                                "source_topic": source_topic,
                                "topics": topics[:3]  # Keep top 3 topics
                            }}
                        )
                    )
            else:
                failed += 1
        
        except Exception as e:
            failed += 1
            if processed % 100 == 0:
                print(f"  ❌ Error: {e}")
        
        # Execute batch updates
        if not dry_run and len(batch_updates) >= batch_size:
            result = coll.bulk_write(batch_updates)
            print(f"  💾 Saved {result.modified_count} updates to database")
            batch_updates = []
    
    # Final batch
    if not dry_run and batch_updates:
        result = coll.bulk_write(batch_updates)
        print(f"\n💾 Saved final {result.modified_count} updates to database")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"  Total processed: {processed:,}")
    print(f"  ✅ Successfully classified: {success:,} ({success/processed*100:.1f}%)")
    print(f"  ❌ Failed: {failed:,} ({failed/processed*100:.1f}%)")
    print(f"\n📈 Topic distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {topic}: {count:,} ({count/success*100:.1f}%)")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes saved to database")
        print("   Run with --apply to save changes")
    else:
        print(f"\n✅ Saved {success:,} classifications to database")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify posts by text content")
    parser.add_argument("--limit", type=int, help="Maximum number of posts to process")
    parser.add_argument("--apply", action="store_true", help="Actually save to database (default is dry run)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for updates")
    
    args = parser.parse_args()
    
    classify_by_content(
        limit=args.limit,
        dry_run=not args.apply,
        batch_size=args.batch_size
    )
