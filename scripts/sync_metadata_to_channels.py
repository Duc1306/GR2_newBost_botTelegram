"""
Đồng bộ tất cả kênh từ channel_metadata → channels collection.

Kênh được đánh dấu `system=True` (không bị xóa khi user unsubscribe).
Kênh chưa có trong channels sẽ được thêm vào pending_channels để worker xử lý.
Kênh đã tồn tại (bất kỳ status) sẽ được bỏ qua.

Usage:
    python scripts/sync_metadata_to_channels.py [--dry-run]
"""
from __future__ import annotations
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.mongo import get_db


def sync_metadata_to_channels(dry_run: bool = False) -> None:
    db = get_db()
    meta_col      = db["channel_metadata"]
    channels_col  = db["channels"]
    pending_col   = db["pending_channels"]

    all_meta = list(meta_col.find({}))
    print(f"channel_metadata: {len(all_meta)} kênh")

    # Lấy username đã có trong channels
    existing = {
        c["username"].lower()
        for c in channels_col.find({}, {"username": 1})
    }
    print(f"channels hiện tại: {len(existing)} kênh")

    to_add = [m for m in all_meta if m["username"].lower() not in existing]
    print(f"Sẽ thêm mới: {len(to_add)} kênh\n")

    if not to_add:
        print("Không có kênh mới cần đồng bộ.")
        return

    added = 0
    skipped = 0
    now = datetime.utcnow()

    for meta in to_add:
        username     = meta["username"].lower()
        display_name = meta.get("title") or meta.get("username")
        channel_link = meta.get("link") or f"https://t.me/{username}"
        platform     = meta.get("platform", "telegram")
        category     = meta.get("category") or meta.get("category_original")

        channel_doc = {
            "username":      username,
            "channel_link":  channel_link,
            "platform":      platform,
            "display_name":  display_name,
            "category":      category,
            "status":        "pending",
            "system":        True,           # đánh dấu là kênh hệ thống — không xóa khi unsubscribe
            "added_at":      now,
            "processed_at":  None,
            "error_message": None,
            "post_count":    0,
        }

        pending_doc = {
            "channel_username": username,
            "channel_link":     channel_link,
            "queued_at":        now,
            "attempts":         0,
        }

        if dry_run:
            print(f"  [DRY-RUN] Sẽ thêm: {username:35} ({category})")
            added += 1
            continue

        try:
            channels_col.insert_one(channel_doc)
            # Chỉ thêm vào pending nếu chưa có
            if not pending_col.find_one({"channel_username": username}):
                pending_col.insert_one(pending_doc)
            print(f"  ✓ Thêm: {username:35} ({category})")
            added += 1
        except Exception as exc:
            print(f"  ✗ Lỗi {username}: {exc}")
            skipped += 1

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Kết quả: {added} thêm mới, {skipped} lỗi")
    if not dry_run:
        print("\nWorker sẽ tự động xử lý các kênh pending trong vòng 30 giây.")
        print("Theo dõi log: channel_queue_worker")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Chỉ hiển thị, không thay đổi DB")
    args = parser.parse_args()
    sync_metadata_to_channels(dry_run=args.dry_run)
