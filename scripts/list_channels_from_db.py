"""
Script hiển thị danh sách các kênh từ database
Xem các kênh đã join và metadata của chúng
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.mongo import get_db
from src.processing.category_mapper import map_category_to_topic


def list_channels_from_db():
    """Hiển thị danh sách kênh từ database"""
    db = get_db()
    collection = db['channel_metadata']
    
    # Lấy tất cả kênh
    channels = list(collection.find({'platform': 'telegram'}).sort('topic_vietnamese', 1))
    
    if not channels:
        print("❌ Không có kênh nào trong database!")
        print("Chạy: python scripts/auto_join_channels.py để join kênh từ channel.json")
        return
    
    print("="*80)
    print(f"📋 DANH SÁCH KÊNH TELEGRAM TRONG DATABASE ({len(channels)} kênh)")
    print("="*80)
    
    # Group by topic
    from collections import defaultdict
    by_topic = defaultdict(list)
    
    for ch in channels:
        topic = ch.get('topic_vietnamese', 'Khác')
        by_topic[topic].append(ch)
    
    # Hiển thị theo từng topic
    for topic in sorted(by_topic.keys()):
        channels_in_topic = by_topic[topic]
        print(f"\n{'='*80}")
        print(f"🏷️  {topic} ({len(channels_in_topic)} kênh)")
        print(f"{'='*80}")
        
        for i, ch in enumerate(channels_in_topic, 1):
            username = ch.get('username', 'unknown')
            title = ch.get('title', username)
            participants = ch.get('participants_count', 0)
            category_en = ch.get('category_original', '')
            
            print(f"{i:2}. @{username:30} | {title[:35]:35}")
            if participants:
                print(f"    👥 {participants:,} thành viên | 📂 {category_en}")
    
    # Tổng kết
    print("\n" + "="*80)
    print("📊 THỐNG KÊ")
    print("="*80)
    for topic in sorted(by_topic.keys()):
        count = len(by_topic[topic])
        print(f"  • {topic:30} : {count:3} kênh")
    print(f"\n  📝 Tổng cộng: {len(channels)} kênh")
    print("="*80)
    
    # Hướng dẫn
    print("\n💡 GỢI Ý:")
    print("  • Fetch dữ liệu: python -m src.ingestion.telegram_worker")
    print("  • Hoặc chạy:     scripts\\fetch_telegram.cmd")
    print("  • Xem API docs:  http://localhost:8000/docs")


if __name__ == "__main__":
    list_channels_from_db()
