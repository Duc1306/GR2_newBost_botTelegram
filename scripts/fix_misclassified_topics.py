"""
Script để sửa lại các topic bị phân loại sai trong database.
Sử dụng rule-based classifier đã cải thiện để reclassify lại toàn bộ posts.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.mongo import get_posts_collection
from src.processing.topic_classifier import TopicClassifier
from pymongo import UpdateOne


def fix_misclassified_topics(batch_size: int = 100, dry_run: bool = False):
    """
    Reclassify tất cả posts trong database với rule-based classifier mới.
    
    Args:
        batch_size: Số lượng posts xử lý mỗi lần
        dry_run: Nếu True, chỉ hiển thị thay đổi không lưu vào DB
    """
    coll = get_posts_collection()
    
    # Đếm tổng số posts
    total = coll.count_documents({})
    print(f"\n📊 Tổng số posts trong database: {total:,}")
    
    if dry_run:
        print("⚠️  CHẾ ĐỘ DRY RUN - Không lưu thay đổi vào database\n")
    
    classifier = TopicClassifier()
    
    # Statistics
    processed = 0
    changed = 0
    unchanged = 0
    no_topic_before = 0
    no_topic_after = 0
    topic_changes = {}  # {old_topic: {new_topic: count}}
    
    # Process in batches
    cursor = coll.find(
        {"text": {"$exists": True, "$ne": ""}},
        {"_id": 1, "id": 1, "text": 1, "lang": 1, "topics": 1}
    ).batch_size(batch_size)
    
    batch_updates = []
    
    for doc in cursor:
        processed += 1
        
        text = doc.get("text", "")
        lang = doc.get("lang")
        old_topics = doc.get("topics", [])
        
        # Classify lại với rule-based classifier mới
        new_topics = classifier.classify(text, lang)
        
        # So sánh thay đổi
        if old_topics != new_topics:
            changed += 1
            
            # Track changes
            old_topic_str = old_topics[0] if old_topics else "(none)"
            new_topic_str = new_topics[0] if new_topics else "(none)"
            
            if old_topic_str not in topic_changes:
                topic_changes[old_topic_str] = {}
            if new_topic_str not in topic_changes[old_topic_str]:
                topic_changes[old_topic_str][new_topic_str] = 0
            topic_changes[old_topic_str][new_topic_str] += 1
            
            # Prepare update
            if not dry_run:
                batch_updates.append(
                    UpdateOne(
                        {"id": doc["id"]},
                        {"$set": {"topics": new_topics}}
                    )
                )
            
            # Log một số thay đổi đầu tiên
            if changed <= 10:
                print(f"  {changed}. ID: {doc['id']}")
                print(f"     OLD: {old_topics}")
                print(f"     NEW: {new_topics}")
                print(f"     Text preview: {text[:100]}...")
                print()
        else:
            unchanged += 1
        
        # Track các posts không có topic
        if not old_topics:
            no_topic_before += 1
        if not new_topics:
            no_topic_after += 1
        
        # Execute batch updates
        if not dry_run and len(batch_updates) >= batch_size:
            result = coll.bulk_write(batch_updates)
            print(f"  💾 Đã lưu {result.modified_count} thay đổi...")
            batch_updates = []
        
        # Progress update
        if processed % 1000 == 0:
            print(f"  ⏳ Đã xử lý: {processed:,}/{total:,} ({processed/total*100:.1f}%)")
    
    # Execute remaining updates
    if not dry_run and batch_updates:
        result = coll.bulk_write(batch_updates)
        print(f"  💾 Đã lưu {result.modified_count} thay đổi cuối cùng...")
    
    # Print summary
    print("\n" + "="*70)
    print("📊 KẾT QUẢ RECLASSIFICATION")
    print("="*70)
    print(f"  Tổng số posts xử lý: {processed:,}")
    print(f"  ✅ Giữ nguyên topic:  {unchanged:,} ({unchanged/processed*100:.1f}%)")
    print(f"  🔄 Thay đổi topic:   {changed:,} ({changed/processed*100:.1f}%)")
    print(f"  ⚠️  Không topic (trước): {no_topic_before:,}")
    print(f"  ⚠️  Không topic (sau):   {no_topic_after:,}")
    
    if topic_changes:
        print("\n📈 CHI TIẾT THAY ĐỔI TOPIC:")
        print("-" * 70)
        for old_topic, new_topics_dict in sorted(topic_changes.items()):
            print(f"\n  {old_topic}:")
            for new_topic, count in sorted(new_topics_dict.items(), key=lambda x: x[1], reverse=True):
                print(f"    → {new_topic}: {count:,} bài")
    
    if dry_run:
        print("\n⚠️  ĐÂY LÀ CHẾ ĐỘ DRY RUN - Không có thay đổi nào được lưu vào database")
        print("   Để áp dụng thay đổi, chạy: python scripts/fix_misclassified_topics.py --apply")
    else:
        print("\n✅ Đã cập nhật database thành công!")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sửa lại các topic bị phân loại sai")
    parser.add_argument("--apply", action="store_true", 
                        help="Áp dụng thay đổi vào database (mặc định là dry run)")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Số lượng posts xử lý mỗi lần (mặc định: 100)")
    
    args = parser.parse_args()
    
    fix_misclassified_topics(
        batch_size=args.batch_size,
        dry_run=not args.apply
    )
