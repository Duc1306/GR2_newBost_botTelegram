"""
Script migrate các kênh từ .env vào database
Chạy 1 lần để chuyển tất cả kênh từ TELEGRAM_CHANNELS sang database
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import env_channels
from src.db.mongo import get_db
from datetime import datetime, timezone


def migrate_env_channels_to_db():
    """
    Migrate các kênh từ ENV vào database
    """
    print("="*80)
    print("🔄 MIGRATE KÊNH TỪ .ENV VÀO DATABASE")
    print("="*80)
    
    # Lấy kênh từ ENV
    env_channel_list = env_channels()
    
    if not env_channel_list:
        print("\n❌ Không có kênh nào trong biến TELEGRAM_CHANNELS trong .env")
        print("💡 Hoặc bạn đã xóa biến này rồi - đó là điều tốt!")
        print("   Sử dụng: python scripts/auto_join_channels.py để join kênh mới")
        return
    
    print(f"\n📋 Tìm thấy {len(env_channel_list)} kênh trong .env")
    print("Đang migrate vào database...\n")
    
    # Kết nối database
    db = get_db()
    collection = db['channel_metadata']
    
    migrated = 0
    already_exists = 0
    failed = 0
    
    for i, username in enumerate(env_channel_list, 1):
        username = username.strip().lstrip('@')
        
        try:
            # Kiểm tra xem kênh đã tồn tại chưa
            existing = collection.find_one({'username': username})
            
            if existing:
                print(f"{i:2}. @{username:30} - ✓ Đã có trong DB")
                already_exists += 1
            else:
                # Thêm kênh mới vào database với metadata cơ bản
                metadata = {
                    'username': username,
                    'platform': 'telegram',
                    'category_original': 'Other',  # Mặc định
                    'topic_vietnamese': 'Khác',    # Mặc định
                    'link': f'https://t.me/{username}',
                    'source': 'env_migration',
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
                
                collection.insert_one(metadata)
                print(f"{i:2}. @{username:30} - ✅ Đã thêm vào DB")
                migrated += 1
        
        except Exception as e:
            print(f"{i:2}. @{username:30} - ❌ Lỗi: {e}")
            failed += 1
    
    # Tổng kết
    print("\n" + "="*80)
    print("📊 KẾT QUẢ MIGRATION")
    print("="*80)
    print(f"✅ Migrate thành công:   {migrated}/{len(env_channel_list)}")
    print(f"✓  Đã có trong DB:       {already_exists}/{len(env_channel_list)}")
    print(f"❌ Thất bại:             {failed}/{len(env_channel_list)}")
    print(f"📝 Tổng cộng:            {len(env_channel_list)} kênh")
    print("="*80)
    
    if migrated > 0:
        print("\n✅ Migration thành công!")
        print("💡 BÂY GIỜ BẠN CÓ THỂ:")
        print("   1. Xóa hoặc comment dòng TELEGRAM_CHANNELS trong .env")
        print("   2. Hệ thống sẽ tự động lấy kênh từ database")
        print("   3. Thêm kênh mới bằng: python scripts/auto_join_channels.py")
        print("   4. Xem kênh: python scripts/list_channels_from_db.py")
    
    if already_exists > 0 and migrated == 0:
        print("\n✓ Tất cả kênh đã có trong database!")
        print("💡 Bạn có thể xóa TELEGRAM_CHANNELS khỏi .env rồi")


if __name__ == "__main__":
    migrate_env_channels_to_db()
