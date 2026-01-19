"""
Script để extract category/topic từ URLs của các bài post có link.
Sử dụng category từ trang báo gốc làm ground truth cho training.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_posts_collection
from src.processing.web_scraper import ArticleScraper
from pymongo import UpdateOne
import time
from typing import Dict


def extract_categories_from_urls(
    batch_size: int = 50,
    limit: int = 1000,
    delay: float = 0.5,
    dry_run: bool = False
):
    """
    Extract categories từ URLs và cập nhật database.
    
    Args:
        batch_size: Số posts xử lý mỗi batch
        limit: Tổng số posts tối đa
        delay: Delay giữa các requests (tránh bị block)
        dry_run: Nếu True, không lưu vào database
    """
    coll = get_posts_collection()
    
    # Lấy các posts có links nhưng chưa có source_topic
    query = {
        "links": {"$exists": True, "$ne": []},
        "$or": [
            {"source_topic": {"$exists": False}},
            {"source_topic": None}
        ]
    }
    
    total = coll.count_documents(query)
    print(f"\n📊 Tìm thấy {total:,} posts có links chưa có source_topic")
    
    if dry_run:
        print("⚠️  CHẾ ĐỘ DRY RUN - Không lưu vào database\n")
    
    # Statistics
    processed = 0
    success = 0
    failed = 0
    topic_counts: Dict[str, int] = {}
    
    # Process in batches
    cursor = coll.find(query, {
        "_id": 1, 
        "id": 1, 
        "text": 1, 
        "links": 1,
        "topics": 1
    }).limit(limit)
    
    batch_updates = []
    
    for doc in cursor:
        if processed >= limit:
            break
        
        processed += 1
        links = doc.get("links", [])
        
        if not links:
            continue
        
        # Try to extract category from first link
        url = links[0]
        
        print(f"\n[{processed}/{min(limit, total)}] Processing: {url[:60]}...")
        
        try:
            # Extract category from URL (with redirect resolution)
            category_from_url = ArticleScraper._extract_category_from_url(url, resolve_redirects=True)
            source_topic = ArticleScraper._map_category_to_topic(category_from_url) if category_from_url else None
            
            if source_topic:
                success += 1
                topic_counts[source_topic] = topic_counts.get(source_topic, 0) + 1
                
                old_topics = doc.get("topics", [])
                old_topic = old_topics[0] if old_topics else "(none)"
                
                print(f"  ✅ Category: {category_from_url} → Topic: {source_topic}")
                if old_topic != source_topic:
                    print(f"     OLD: {old_topic} | NEW: {source_topic}")
                
                if not dry_run:
                    batch_updates.append(
                        UpdateOne(
                            {"id": doc["id"]},
                            {"$set": {
                                "source_category": category_from_url,
                                "source_topic": source_topic,
                                "topics": [source_topic]  # Override với ground truth
                            }}
                        )
                    )
            else:
                failed += 1
                print(f"  ❌ Could not extract category from URL")
                
                # Fallback: Try scraping the page (slower, only every 20th)
                if processed % 20 == 0:  # Reduced frequency to save time
                    print(f"     Trying full scrape...")
                    time.sleep(delay)
                    
                    article = ArticleScraper.scrape_article(url)
                    if article and article.get('source_topic'):
                        source_topic = article['source_topic']
                        source_category = article.get('category')
                        success += 1
                        failed -= 1
                        topic_counts[source_topic] = topic_counts.get(source_topic, 0) + 1
                        
                        print(f"  ✅ Scraped - Category: {source_category} → Topic: {source_topic}")
                        
                        if not dry_run:
                            batch_updates.append(
                                UpdateOne(
                                    {"id": doc["id"]},
                                    {"$set": {
                                        "source_category": source_category,
                                        "source_topic": source_topic,
                                        "topics": [source_topic],
                                        "full_article": article  # Bonus: save full article
                                    }}
                                )
                            )
                    else:
                        print(f"     Failed to scrape article content")
        
        except Exception as e:
            failed += 1
            print(f"  ❌ Error: {e}")
        
        # Execute batch updates
        if not dry_run and len(batch_updates) >= batch_size:
            result = coll.bulk_write(batch_updates)
            print(f"\n  💾 Saved {result.modified_count} updates to database")
            batch_updates = []
        
        # Progress update
        if processed % 50 == 0:
            print(f"\n📊 Progress: {processed}/{min(limit, total)} | Success: {success} | Failed: {failed}")
            print(f"   Topic distribution: {topic_counts}\n")
    
    # Save remaining updates
    if not dry_run and batch_updates:
        result = coll.bulk_write(batch_updates)
        print(f"\n  💾 Saved {result.modified_count} final updates")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"  Total processed: {processed:,}")
    print(f"  ✅ Successfully extracted: {success:,} ({success/max(processed,1)*100:.1f}%)")
    print(f"  ❌ Failed: {failed:,} ({failed/max(processed,1)*100:.1f}%)")
    
    if topic_counts:
        print(f"\n📈 TOPIC DISTRIBUTION:")
        print("-" * 80)
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {topic}: {count:,} ({count/success*100:.1f}%)")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes saved to database")
        print("   Run with --apply to save changes")
    else:
        print("\n✅ Successfully updated database!")
        print("\n📝 Next steps:")
        print("   1. Review the extracted topics")
        print("   2. Train ML model with ground truth: python scripts\\train_ml_classifier.py")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract categories from news URLs as ground truth"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to database (default is dry run)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for database updates (default: 50)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of posts to process (default: 1000)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
    )
    
    args = parser.parse_args()
    
    extract_categories_from_urls(
        batch_size=args.batch_size,
        limit=args.limit,
        delay=args.delay,
        dry_run=not args.apply
    )
