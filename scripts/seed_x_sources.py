"""Seed tài khoản X (Twitter) vào MongoDB collection channel_metadata.
Cùng cấu trúc với kênh Telegram — chỉ khác platform = "twitter".

Chạy:
  python scripts/seed_x_sources.py           # seed mặc định
  python scripts/seed_x_sources.py --dry-run  # xem trước, không ghi DB
  python scripts/seed_x_sources.py --reset    # xoá hết rồi seed lại
"""
from __future__ import annotations
import sys
import argparse
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Danh sách tài khoản X mẫu — chỉnh sửa tuỳ dự án
# ============================================================
DEFAULT_X_SOURCES = [
    # ── Tin tức Việt Nam ──────────────────────────────────────
    {"username": "VNExpress",       "category": "Thế giới",  "topic_hint": "general"},
    {"username": "tuoitrenews",     "category": "Thế giới",  "topic_hint": "general"},
    {"username": "ThanhNienNews",   "category": "Thế giới",  "topic_hint": "general"},

    # ── Công nghệ & AI ────────────────────────────────────────
    {"username": "TechCrunch",      "category": "Công nghệ", "topic_hint": "tech"},
    {"username": "TheVerge",        "category": "Công nghệ", "topic_hint": "tech"},
    {"username": "OpenAI",          "category": "Công nghệ", "topic_hint": "tech"},
    {"username": "GoogleAI",        "category": "Công nghệ", "topic_hint": "tech"},

    # ── Kinh tế & Tài chính ───────────────────────────────────
    {"username": "business",        "category": "Kinh tế",   "topic_hint": "economy"},
    {"username": "Reuters",         "category": "Kinh tế",   "topic_hint": "economy"},
    {"username": "Forbes",          "category": "Kinh tế",   "topic_hint": "economy"},

    # ── Crypto ────────────────────────────────────────────────
    {"username": "coindesk",        "category": "Crypto",    "topic_hint": "crypto"},
    {"username": "cointelegraph",   "category": "Crypto",    "topic_hint": "crypto"},

    # ── Quốc tế ───────────────────────────────────────────────
    {"username": "BBCBreaking",     "category": "Thế giới",  "topic_hint": "world"},
    {"username": "AP",              "category": "Thế giới",  "topic_hint": "world"},
]


def build_doc(src: dict) -> dict:
    """Tạo document chuẩn cho channel_metadata."""
    return {
        "platform":    "twitter",
        "username":    src["username"],
        "link":        f"https://x.com/{src['username']}",
        "category":    src["category"],
        "topic_hint":  src.get("topic_hint", ""),
        "is_active":   True,
        "source_type": "x_account",
        "added_at":    datetime.now(UTC),
    }


def seed(dry_run: bool = False, reset: bool = False) -> None:
    from src.db.mongo import get_db
    db = get_db()
    col = db["channel_metadata"]

    if reset and not dry_run:
        deleted = col.delete_many({"platform": "twitter"}).deleted_count
        print(f"🗑️  Đã xoá {deleted} X sources cũ")

    inserted = skipped = 0
    for src in DEFAULT_X_SOURCES:
        doc = build_doc(src)

        if dry_run:
            print(f"  [DRY] @{doc['username']} | {doc['category']}")
            continue

        result = col.update_one(
            {"platform": "twitter", "username": doc["username"]},
            {"$set": doc},
            upsert=True,
        )
        if result.upserted_id:
            inserted += 1
            print(f"  ✓ Thêm mới: @{doc['username']} ({doc['category']})")
        else:
            skipped += 1

    if not dry_run:
        print(f"\n✅ Seed X sources hoàn tất: {inserted} mới, {skipped} đã tồn tại")
        print(f"   Tổng trong DB: {col.count_documents({'platform': 'twitter'})} tài khoản X")
    else:
        print(f"\n[DRY RUN] Sẽ upsert {len(DEFAULT_X_SOURCES)} tài khoản — không ghi gì vào DB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed X/Twitter sources vào MongoDB")
    parser.add_argument("--dry-run", action="store_true", help="Xem trước, không ghi DB")
    parser.add_argument("--reset",   action="store_true", help="Xoá hết X sources rồi seed lại")
    args = parser.parse_args()

    print("=" * 50)
    print(" Seed X/Twitter Sources → channel_metadata")
    print("=" * 50 + "\n")
    seed(dry_run=args.dry_run, reset=args.reset)
