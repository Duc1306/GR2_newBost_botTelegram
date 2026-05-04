"""Backfill links cho posts đã có trong DB nhưng thiếu links.

Script này:
1. Query DB tìm posts của kênh chỉ định (hoặc tất cả kênh Telegram) mà links=[]
2. Fetch lại đúng các message ID đó từ Telegram bằng get_messages()
3. Extract links từ entities + web preview rồi update DB

Chạy:
  python scripts/backfill_links.py                    # tất cả kênh
  python scripts/backfill_links.py baodantri          # chỉ kênh baodantri
  python scripts/backfill_links.py baodantri tuoitre  # nhiều kênh
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

# Thêm root vào sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageEntityTextUrl, MessageMediaWebPage

from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING
from src.db.mongo import get_db, get_posts_collection

SESSION_NAME = "telegram_session"
BATCH_SIZE = 200  # Số message IDs fetch mỗi lần (Telegram giới hạn ~100-200)


def build_client() -> TelegramClient:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise RuntimeError("Thiếu TELEGRAM_API_ID / TELEGRAM_API_HASH trong .env")
    if TELEGRAM_SESSION_STRING:
        return TelegramClient(StringSession(TELEGRAM_SESSION_STRING), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    return TelegramClient(SESSION_NAME, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)


def extract_links_from_message(m) -> list[str]:
    """Extract tất cả links từ message: text regex + entities + web preview."""
    from src.processing.cleaning import extract_links as regex_extract_links
    raw_text = m.message or ""
    _, links = regex_extract_links(raw_text)

    # Entity-based hidden URLs (MessageEntityTextUrl)
    if m.entities:
        for entity in m.entities:
            if isinstance(entity, MessageEntityTextUrl) and entity.url:
                if entity.url not in links:
                    links.append(entity.url)

    # Web preview URL (MessageMediaWebPage)
    if m.media and isinstance(m.media, MessageMediaWebPage):
        wp_url = getattr(m.media.webpage, 'url', None)
        if wp_url and wp_url not in links:
            links.append(wp_url)

    return links


async def backfill_channel(client: TelegramClient, channel: str) -> int:
    """
    Backfill links cho tất cả posts trong DB của kênh này mà links=[].
    Trả về số posts đã được cập nhật.
    """
    coll = get_posts_collection()

    # Tìm tất cả posts của kênh có links rỗng
    empty_link_posts = list(coll.find(
        {"source": channel, "platform": "telegram", "links": {"$in": [[], None]}},
        {"id": 1, "source_id": 1}
    ))

    if not empty_link_posts:
        print(f"  [{channel}] Không có post nào thiếu link → bỏ qua")
        return 0

    print(f"  [{channel}] Tìm thấy {len(empty_link_posts)} posts thiếu link → đang backfill...")

    # Group source_id thành int message IDs
    msg_id_map: dict[int, str] = {}  # telegram_msg_id → post.id
    for p in empty_link_posts:
        try:
            msg_id_map[int(p["source_id"])] = p["id"]
        except (ValueError, KeyError):
            pass

    if not msg_id_map:
        return 0

    msg_ids = list(msg_id_map.keys())
    updated = 0

    # Fetch theo batch
    for i in range(0, len(msg_ids), BATCH_SIZE):
        batch_ids = msg_ids[i:i + BATCH_SIZE]
        try:
            messages = await client.get_messages(channel, ids=batch_ids)
        except FloodWaitError as e:
            print(f"    FloodWait {e.seconds}s, chờ...")
            await asyncio.sleep(e.seconds)
            messages = await client.get_messages(channel, ids=batch_ids)
        except Exception as e:
            print(f"    Lỗi fetch batch {i}-{i+BATCH_SIZE}: {e}")
            continue

        for m in messages:
            if m is None:
                continue  # Message đã bị xóa
            links = extract_links_from_message(m)
            if not links:
                continue  # Vẫn không có link → bỏ qua

            post_id = msg_id_map.get(m.id)
            if not post_id:
                continue

            coll.update_one(
                {"id": post_id},
                {"$set": {"links": links}}
            )
            updated += 1

        print(f"    Batch {i//BATCH_SIZE + 1}: đã update {updated}/{len(msg_ids)} posts")

    return updated


async def main(target_channels: list[str]) -> None:
    db = get_db()

    if not target_channels:
        # Lấy tất cả kênh Telegram từ DB
        ch_docs = list(db['channel_metadata'].find(
            {'platform': 'telegram', 'is_active': {'$ne': False}},
            {'username': 1}
        ))
        target_channels = [c['username'] for c in ch_docs if c.get('username')]
        print(f"Backfill tất cả {len(target_channels)} kênh Telegram trong DB")
    else:
        print(f"Backfill {len(target_channels)} kênh: {', '.join(target_channels)}")

    client = build_client()
    total_updated = 0

    async with client:
        for idx, ch in enumerate(target_channels, 1):
            print(f"\n[{idx}/{len(target_channels)}] {ch}")
            try:
                n = await backfill_channel(client, ch)
                total_updated += n
                if n > 0:
                    print(f"  ✓ {n} posts đã được cập nhật link")
            except Exception as e:
                print(f"  ✗ Lỗi kênh {ch}: {e}")

    print(f"\n✅ Hoàn tất! Tổng cộng đã cập nhật {total_updated} posts.")


if __name__ == "__main__":
    channels = sys.argv[1:]  # Tên kênh từ command line (không có @)
    asyncio.run(main(channels))
