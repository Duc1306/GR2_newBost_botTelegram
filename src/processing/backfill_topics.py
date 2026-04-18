"""Backfill topics for existing posts that are missing or empty topics.
Run: python -m src.processing.backfill_topics [--limit 10000]
"""
from __future__ import annotations
import sys
from typing import List
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from src.db.mongo import get_posts_collection
from src.processing.topic_classifier import classify_post_topics
from src.processing.lang import detect_language

_BATCH_SIZE = 500


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
    batch: list[UpdateOne] = []

    def _flush(ops: list) -> int:
        if not ops:
            return 0
        try:
            result = coll.bulk_write(ops, ordered=False)
            return result.modified_count
        except BulkWriteError as bwe:
            return bwe.details.get("nModified", 0)

    for doc in cursor:
        text = doc.get("text", "")
        lang = doc.get("lang") or detect_language(text)
        topics = classify_post_topics(text, lang)
        if topics:
            batch.append(UpdateOne({"id": doc["id"]}, {"$set": {"topics": topics}}))
        count += 1
        if len(batch) >= _BATCH_SIZE:
            updated += _flush(batch)
            batch = []
            print(f"Processed {count} docs, updated {updated}")

    updated += _flush(batch)
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
