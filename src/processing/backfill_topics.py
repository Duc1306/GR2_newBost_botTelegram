"""Backfill topics and geo for existing posts that are missing them.

Run:
    # Xem trước số bài cần xử lý (không tốn token):
    python -m src.processing.backfill_topics --count

    # Chạy đầy đủ (rule-based + OpenAI fallback + geo):
    python -m src.processing.backfill_topics

    # Chỉ classify topic bằng OpenAI (bỏ qua rule-based):
    python -m src.processing.backfill_topics --ai-only

    # Chỉ backfill trường geo:
    python -m src.processing.backfill_topics --geo-only

    # Giới hạn số bài xử lý:
    python -m src.processing.backfill_topics --limit 500
"""
from __future__ import annotations
import asyncio
import sys
import time
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from src.db.mongo import get_posts_collection
from src.processing.topic_classifier import classify_post_topics
from src.processing.lang import detect_language
from src.processing.ai_topic_detector import classify_post_topic_with_ai, classify_geo_with_ai

_BATCH_SIZE = 200           # số bài mỗi batch ghi DB
_AI_CONCURRENCY = 5         # số lượng OpenAI calls đồng thời (tránh rate-limit)
_MIN_TEXT_LEN = 30          # bài ngắn hơn thế này → bỏ qua, không gọi AI


def _flush(coll, ops: list) -> int:
    if not ops:
        return 0
    try:
        result = coll.bulk_write(ops, ordered=False)
        return result.modified_count
    except BulkWriteError as bwe:
        return bwe.details.get("nModified", 0)


async def _ai_topics_batch(texts: list[str]) -> list[list[str]]:
    """Gọi classify_post_topic_with_ai song song, giới hạn _AI_CONCURRENCY luồng."""
    sem = asyncio.Semaphore(_AI_CONCURRENCY)

    async def _one(text: str) -> list[str]:
        async with sem:
            return await classify_post_topic_with_ai(text)

    return list(await asyncio.gather(*[_one(t) for t in texts]))


async def _ai_geo_batch(texts: list[str]) -> list[str | None]:
    """Gọi classify_geo_with_ai song song, giới hạn _AI_CONCURRENCY luồng."""
    sem = asyncio.Semaphore(_AI_CONCURRENCY)

    async def _one(text: str) -> str | None:
        async with sem:
            return await classify_geo_with_ai(text)

    return list(await asyncio.gather(*[_one(t) for t in texts]))


def _missing_topics_query() -> dict:
    return {
        "$or": [
            {"topics": {"$exists": False}},
            {"topics": {"$size": 0}},
            {"topics": None},
        ]
    }


def _missing_geo_query() -> dict:
    return {
        "$or": [
            {"geo": {"$exists": False}},
            {"geo": None},
            {"geo": ""},
        ]
    }


def count_missing(verbose: bool = True) -> dict:
    """Đếm số bài thiếu topic / geo — chạy trước khi backfill để ước tính chi phí OpenAI."""
    coll = get_posts_collection()
    missing_topics = coll.count_documents(_missing_topics_query())
    missing_geo = coll.count_documents(_missing_geo_query())
    total = coll.count_documents({})

    if verbose:
        pct_t = f"{missing_topics/total*100:.1f}%" if total else "—"
        pct_g = f"{missing_geo/total*100:.1f}%" if total else "—"
        print("=" * 58)
        print(f"  Tổng bài viết trong DB  : {total:,}")
        print(f"  Thiếu topics            : {missing_topics:,}  ({pct_t})")
        print(f"  Thiếu geo               : {missing_geo:,}  ({pct_g})")
        print("-" * 58)
        # gpt-4o-mini: ~$0.15/1M input tokens, ước ~150 tokens/bài (topic) & ~100 tokens/bài (geo)
        est_topic_cost = missing_topics * 150 / 1_000_000 * 0.15
        est_geo_cost   = missing_geo    * 100 / 1_000_000 * 0.15
        print(f"  Chi phí OpenAI ước tính (topics) : ~${est_topic_cost:.4f} USD")
        print(f"  Chi phí OpenAI ước tính (geo)    : ~${est_geo_cost:.4f} USD")
        print("=" * 58)
        print("  Chạy thực sự: python -m src.processing.backfill_topics")
        print("=" * 58)

    return {"total": total, "missing_topics": missing_topics, "missing_geo": missing_geo}


async def backfill_async(limit: int = 10000, geo_only: bool = False, ai_only: bool = False) -> dict:
    """Thực hiện backfill. Trả về dict thống kê kết quả."""
    coll = get_posts_collection()
    stats: dict = {
        "rule_updated": 0,
        "ai_updated": 0,
        "geo_updated": 0,
        "ai_skipped_short": 0,
    }
    t0 = time.time()

    # ── Phase 1: Topic backfill ──────────────────────────────────────────────
    if not geo_only:
        cursor = coll.find(
            _missing_topics_query(), {"id": 1, "text": 1, "lang": 1}
        ).limit(limit)

        rule_batch: list[UpdateOne] = []
        ai_pending: list[dict] = []

        for doc in cursor:
            text = doc.get("text", "")
            if ai_only:
                if len(text.strip()) >= _MIN_TEXT_LEN:
                    ai_pending.append(doc)
                else:
                    stats["ai_skipped_short"] += 1
            else:
                lang = doc.get("lang") or detect_language(text)
                topics = classify_post_topics(text, lang)
                if topics:
                    rule_batch.append(UpdateOne({"id": doc["id"]}, {"$set": {"topics": topics}}))
                    if len(rule_batch) >= _BATCH_SIZE:
                        stats["rule_updated"] += _flush(coll, rule_batch)
                        rule_batch = []
                else:
                    # Rule-based thất bại → đưa vào hàng đợi AI (nếu text đủ dài)
                    if len(text.strip()) >= _MIN_TEXT_LEN:
                        ai_pending.append(doc)
                    else:
                        stats["ai_skipped_short"] += 1

        stats["rule_updated"] += _flush(coll, rule_batch)

        ai_total = len(ai_pending)
        print(
            f"[topics] Rule-based: cập nhật {stats['rule_updated']:,} bài  |  "
            f"Cần AI: {ai_total:,}  |  Bỏ qua (quá ngắn): {stats['ai_skipped_short']:,}"
        )

        if ai_total > 0:
            from src.processing.ai_topic_detector import _RPD_EXHAUSTED  # noqa: PLC0415
            ai_batch: list[UpdateOne] = []
            for i in range(0, ai_total, _BATCH_SIZE):
                import src.processing.ai_topic_detector as _aitd
                if _aitd._RPD_EXHAUSTED:
                    print("[topics/AI] ⚠️  Daily RPD limit hết — dừng. Chạy lại vào ngày mai.")
                    break
                chunk = ai_pending[i:i + _BATCH_SIZE]
                texts = [d.get("text", "") for d in chunk]
                results = await _ai_topics_batch(texts)
                for doc, topics in zip(chunk, results):
                    if topics:
                        ai_batch.append(UpdateOne({"id": doc["id"]}, {"$set": {"topics": topics}}))
                if len(ai_batch) >= _BATCH_SIZE:
                    stats["ai_updated"] += _flush(coll, ai_batch)
                    ai_batch = []
                done = min(i + _BATCH_SIZE, ai_total)
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = int((ai_total - done) / rate) if rate > 0 else 0
                print(f"[topics/AI] {done}/{ai_total}  ({rate:.1f} bài/s  ETA {eta}s)")

            stats["ai_updated"] += _flush(coll, ai_batch)

        print(
            f"[topics] ✓ Hoàn tất  "
            f"rule={stats['rule_updated']:,}  AI={stats['ai_updated']:,}  "
            f"bỏ_qua={stats['ai_skipped_short']:,}  "
            f"({time.time() - t0:.0f}s)"
        )

    # ── Phase 2: Geo backfill ────────────────────────────────────────────────
    geo_docs = list(coll.find(_missing_geo_query(), {"id": 1, "text": 1, "source": 1}).limit(limit))
    geo_total = len(geo_docs)
    print(f"[geo] {geo_total:,} bài cần phân loại địa lý …")

    if geo_total > 0:
        from src.processing.geo_classifier import classify_geo_rule_based
        import src.processing.ai_topic_detector as _aitd

        geo_rule_batch: list[UpdateOne] = []
        geo_ai_pending: list[dict] = []
        geo_rule_skipped_short = 0

        # Bước 2a: Rule-based (miễn phí)
        for doc in geo_docs:
            text = doc.get("text", "")
            source = doc.get("source", "")
            region = classify_geo_rule_based(text, source=source)
            if region:
                geo_rule_batch.append(UpdateOne({"id": doc["id"]}, {"$set": {"geo": region}}))
            elif len(text.strip()) >= _MIN_TEXT_LEN:
                geo_ai_pending.append(doc)
            else:
                geo_rule_skipped_short += 1

        stats["geo_updated"] += _flush(coll, geo_rule_batch)
        geo_ai_total = len(geo_ai_pending)
        print(
            f"[geo] Rule-based: cập nhật {len(geo_rule_batch):,}  |  "
            f"Cần AI: {geo_ai_total:,}  |  Bỏ qua (quá ngắn): {geo_rule_skipped_short:,}"
        )

        # Bước 2b: AI fallback cho những bài rule-based không xác định được
        geo_batch: list[UpdateOne] = []
        for i in range(0, geo_ai_total, _BATCH_SIZE):
            if _aitd._RPD_EXHAUSTED:
                print(f"[geo] ⚠️  Daily RPD limit hết — dừng ở bài {i}/{geo_ai_total}. Chạy lại vào ngày mai.")
                break
            chunk = geo_ai_pending[i:i + _BATCH_SIZE]
            texts = [d.get("text", "") for d in chunk]
            regions = await _ai_geo_batch(texts)
            for doc, region in zip(chunk, regions):
                if region:
                    geo_batch.append(UpdateOne({"id": doc["id"]}, {"$set": {"geo": region}}))
            if len(geo_batch) >= _BATCH_SIZE:
                stats["geo_updated"] += _flush(coll, geo_batch)
                geo_batch = []
            done = min(i + _BATCH_SIZE, geo_ai_total)
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = int((geo_ai_total - done) / rate) if rate > 0 else 0
            print(f"[geo/AI] {done}/{geo_ai_total}  ({rate:.1f} bài/s  ETA {eta}s)")

        stats["geo_updated"] += _flush(coll, geo_batch)

    print(
        f"[geo] ✓ Hoàn tất  geo={stats['geo_updated']:,}  "
        f"tổng_thời_gian={time.time() - t0:.0f}s"
    )
    return stats


def backfill(limit: int = 10000, geo_only: bool = False, ai_only: bool = False) -> dict:
    return asyncio.run(backfill_async(limit=limit, geo_only=geo_only, ai_only=ai_only))


if __name__ == "__main__":
    lim = 10000
    geo_only = "--geo-only" in sys.argv
    ai_only  = "--ai-only"  in sys.argv
    do_count = "--count"    in sys.argv

    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            try:
                lim = int(sys.argv[i + 1])
            except Exception:
                pass

    if do_count:
        count_missing()
    else:
        backfill(lim, geo_only=geo_only, ai_only=ai_only)
