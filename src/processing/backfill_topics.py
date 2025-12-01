"""Backfill topics for existing posts that are missing or empty topics.
Run: python -m src.processing.backfill_topics [--limit 10000]
"""
from __future__ import annotations
import sys
from typing import List
from src.db.mongo import get_posts_collection
from src.processing.topic_classifier import classify_post_topics
from src.processing.lang import detect_language


def backfill(limit: int = 10000) -> None:
    coll = get_posts_collection()
    query = {
        "$or": [
            {"topics": {"$exists": False}},
            {"topics": {"$size": 0}},
            {"topics": None},
        ]
    }
    cursor = coll.find(query).limit(limit)
    count = 0
    updated = 0
    for doc in cursor:
        text = doc.get("text", "")
        lang = doc.get("lang") or detect_language(text)
        topics = classify_post_topics(text, lang)
        if topics:
            res = coll.update_one({"id": doc["id"]}, {"$set": {"topics": topics}})
            if res.modified_count:
                updated += 1
        count += 1
        if count % 500 == 0:
            print(f"Processed {count} docs, updated {updated}")
    print(f"Done. Scanned {count}, updated {updated} posts.")


if __name__ == "__main__":
    lim = 10000
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            try:
                lim = int(sys.argv[i+1])
            except Exception:
                pass
    backfill(lim)
