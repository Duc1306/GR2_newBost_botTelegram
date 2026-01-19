"""Tạo indexes cho MongoDB collections.
Chạy một lần sau khi thiết lập DB.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.mongo import get_posts_collection

def create_indexes():
    posts = get_posts_collection()
    
    # Unique index cho id (composite: source:source_id)
    posts.create_index("id", unique=True)
    print(" Created unique index on 'id'")
    
    # Unique index cho dedupe_key để tránh trùng lặp nội dung
    posts.create_index("dedupe_key", unique=True)
    print(" Created unique index on 'dedupe_key'")
    
    # Index thời gian để sort nhanh
    posts.create_index([("created_at", -1)])
    print(" Created descending index on 'created_at'")
    
    # Index nguồn và chủ đề để filter
    posts.create_index("source")
    posts.create_index("topics")
    print(" Created indexes on 'source' and 'topics'")
    
    print("\ Tất cả indexes đã được tạo!")

if __name__ == "__main__":
    create_indexes()
