"""Xóa bài từ 2009 đến 2020 (trước 2021-01-01) trong MongoDB."""
from datetime import datetime
from src.db.mongo import get_db

db = get_db()
posts = db["posts"]

cutoff = datetime(2021, 1, 1)

count = posts.count_documents({"created_at": {"$lt": cutoff}})
print(f"Số bài sẽ bị xóa (trước 2021): {count}")

result = posts.delete_many({"created_at": {"$lt": cutoff}})
print(f"Đã xóa: {result.deleted_count} bài")
print(f"Còn lại trong DB: {posts.count_documents({})} bài")
