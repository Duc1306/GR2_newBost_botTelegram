"""
Script để sync category từ channel.json vào database MongoDB
Chạy script này sau khi cập nhật category trong channel.json
"""
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.mongo import get_db
from src.processing.category_mapper import map_category_to_topic
from datetime import datetime, timezone


def sync_channel_categories(json_path: str = "channel.json", dry_run: bool = True):
    """
    Sync category từ channel.json vào MongoDB channel_metadata collection
    
    Args:
        json_path: Path đến file channel.json
        dry_run: Nếu True, chỉ hiển thị thay đổi mà không lưu vào DB
    """
    print("="*80)
    print("🔄 SYNC CHANNEL CATEGORIES VÀO DATABASE")
    print("="*80)
    
    # Đọc channel.json
    if not os.path.exists(json_path):
        print(f"\n❌ Không tìm thấy file: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        channels_data = json.load(f)
    
    print(f"\n📋 Đọc {len(channels_data)} kênh từ {json_path}")
    
    if dry_run:
        print("\n⚠️ DRY RUN MODE - Không lưu thay đổi vào database!")
    else:
        print("\n✅ APPLY MODE - Thay đổi sẽ được lưu vào database!")
    
    # Kết nối database
    db = get_db()
    collection = db['channel_metadata']
    
    updated = 0
    created = 0
    skipped = 0
    errors = 0
    
    print("\n" + "-"*80)
    
    for channel in channels_data:
        username = channel.get('username', '').strip().lstrip('@')
        category_en = channel.get('category', '').strip()
        
        # Map sang tiếng Việt
        category = map_category_to_topic(category_en)
        
        if not username:
            skipped += 1
            continue
        
        try:
            # Tìm channel trong database
            existing = collection.find_one({'username': username})
            
            if existing:
                old_category = existing.get('category')
                
                # Kiểm tra nếu category khác
                if old_category != category:
                    if dry_run:
                        print(f"Would update @{username:30} | {old_category:20} → {category}")
                    else:
                        collection.update_one(
                            {'username': username},
                            {
                                '$set': {
                                    'category': category,
                                    'updated_at': datetime.now(timezone.utc)
                                }
                            }
                        )
                        print(f"✅ Updated @{username:30} | {old_category:20} → {category}")
                    updated += 1
                else:
                    if dry_run and updated + created < 5:  # Show first 5 unchanged
                        print(f"   Skipped @{username:30} | {category:20} (unchanged)")
                    skipped += 1
            else:
                # Tạo mới nếu chưa có
                if dry_run:
                    print(f"Would create @{username:30} | Category: {category} ({category_en})")
                else:
                    collection.insert_one({
                        'username': username,
                        'category': category,
                        'category_en': category_en,  # Lưu cả tiếng Anh
                        'link': channel.get('link', ''),
                        'platform': channel.get('platform', 'telegram'),
                        'created_at': datetime.now(timezone.utc),
                        'updated_at': datetime.now(timezone.utc),
                        'is_active': True
                    })
                    print(f"✨ Created  @{username:30} | Category: {category}")
                created += 1
                
        except Exception as e:
            errors += 1
            print(f"❌ Error processing @{username}: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"✅ Updated:  {updated:,}")
    print(f"✨ Created:  {created:,}")
    print(f"⚠️ Skipped:  {skipped:,}")
    print(f"❌ Errors:   {errors:,}")
    
    if dry_run:
        print("\n⚠️ This was a DRY RUN. To apply changes, run:")
        print("   python scripts/sync_channel_categories.py --apply")
    else:
        print("\n✅ Sync hoàn tất! Database đã được cập nhật.")
        print("\n💡 Bây giờ bạn có thể chạy:")
        print("   python scripts/reclassify_with_channel_categories.py --apply")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync channel categories from JSON to MongoDB")
    parser.add_argument("--json", type=str, default="channel.json", help="Path to channel.json file")
    parser.add_argument("--apply", action="store_true", help="Apply changes (not dry run)")
    
    args = parser.parse_args()
    
    sync_channel_categories(
        json_path=args.json,
        dry_run=not args.apply
    )
