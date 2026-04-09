"""Channel subscription API endpoints."""
from __future__ import annotations
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime
from loguru import logger
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.api.auth import get_current_user
from src.db.mongo import get_db
from src.models.channel import SubscribeChannelRequest, BulkSubscribeRequest, ChannelWithSummary

router = APIRouter(prefix="/user/channels", tags=["Channel Subscriptions"])

# Path to the channel catalog JSON (relative to project root)
_CATALOG_PATH = Path(__file__).resolve().parents[2] / "channel.json"

# ---------------------------------------------------------------------------
# Catalog: all 106 curated channels from channel.json, grouped by category
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def get_channel_catalog(current_username: str = Depends(get_current_user)):
    """Trả về toàn bộ danh mục kênh gợi ý (từ channel.json), nhóm theo category."""
    db = get_db()

    # Load catalog
    try:
        catalog: list[dict] = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    # User subscriptions for cross-reference
    user_doc = db["users"].find_one({"username": current_username})
    subscribed: set[str] = set()
    if user_doc:
        subs = db["user_channels"].find(
            {"user_id": str(user_doc["_id"])}, {"channel_username": 1}
        )
        subscribed = {s["channel_username"].lower() for s in subs}

    # Channel status/post_count from DB (only for channels already processed)
    db_channels = {
        c["username"]: c
        for c in db["channels"].find({}, {"username": 1, "status": 1, "post_count": 1, "display_name": 1})
    }

    # Build response grouped by category
    groups: dict[str, list] = {}
    for ch in catalog:
        username = ch["username"].strip().lower()
        category = ch.get("category", "Other").strip()
        db_doc = db_channels.get(username, {})
        groups.setdefault(category, []).append({
            "username": username,
            "display_name": db_doc.get("display_name") or ch.get("display_name"),
            "link": ch.get("link", f"https://t.me/{username}"),
            "category": category,
            "status": db_doc.get("status"),          # None if not yet in DB
            "post_count": db_doc.get("post_count", 0),
            "subscribed": username in subscribed,
        })

    # Return as sorted list of {category, channels[]}
    return [
        {"category": cat, "channels": sorted(chs, key=lambda c: c["username"])}
        for cat, chs in sorted(groups.items())
    ]

# ---------------------------------------------------------------------------
# Discover: all channels in DB (for suggestions panel)
# ---------------------------------------------------------------------------

@router.get("/discover")
async def discover_channels(
    current_username: str = Depends(get_current_user),
):
    """Trả về tất cả kênh đang có trong DB để hiển thị gợi ý."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    user_id = str(user_doc["_id"]) if user_doc else None

    # All channels in system (exclude errors)
    channels = list(db["channels"].find(
        {"status": {"$ne": "error"}},
        {"_id": 0, "username": 1, "display_name": 1, "channel_link": 1, "category": 1},
    ))

    # Count posts live from posts collection (accurate)
    for ch in channels:
        ch["post_count"] = db["posts"].count_documents({"source": ch["username"]})

    # Sort by actual post count desc
    channels.sort(key=lambda c: c["post_count"], reverse=True)

    # Set of usernames this user already follows
    subscribed = set()
    if user_id:
        subs = db["user_channels"].find({"user_id": user_id}, {"channel_username": 1})
        subscribed = {s["channel_username"] for s in subs}

    for ch in channels:
        ch["subscribed"] = ch["username"] in subscribed

    return channels

_TGLINK_RE = re.compile(
    r"^(?:https?://)?t(?:elegram)?\.me/([A-Za-z0-9_]{3,64})"
    r"|^@([A-Za-z0-9_]{3,64})$"
    r"|^([A-Za-z0-9_]{3,64})$",
    re.IGNORECASE,
)


def parse_channel_username(raw: str) -> str:
    """Extract bare username from a t.me link, @handle, or plain username."""
    raw = raw.strip()
    m = _TGLINK_RE.match(raw)
    if not m:
        raise HTTPException(
            status_code=422,
            detail="Link kênh không hợp lệ. Dùng định dạng: t.me/ten_kenh hoặc @ten_kenh",
        )
    username = m.group(1) or m.group(2) or m.group(3)
    return username.lstrip("@").lower()


def normalize_link(username: str) -> str:
    return f"t.me/{username}"


def _subscribe_one(db, user_id: str, raw_link: str) -> dict:
    """
    Core subscribe logic. Returns a result dict with status/message.
    Raises HTTPException on hard errors (bad link format, DB errors).
    Returns {"status": "duplicate"} if already subscribed (soft skip).
    """
    channels_col = db["channels"]
    user_channels_col = db["user_channels"]

    username = parse_channel_username(raw_link)
    channel_link = normalize_link(username)

    # Already subscribed? → soft skip
    if user_channels_col.find_one({"user_id": user_id, "channel_username": username}):
        return {"channel_link": channel_link, "username": username,
                "status": "duplicate", "message": "Bạn đã đăng ký kênh này rồi."}

    channel_doc = channels_col.find_one({"username": username})
    if channel_doc is None:
        now = datetime.utcnow()
        channel_doc = {
            "channel_link": channel_link, "username": username,
            "display_name": None, "status": "pending",
            "added_at": now, "processed_at": None,
            "error_message": None, "post_count": 0,
        }
        result = channels_col.insert_one(channel_doc)
        channel_doc["_id"] = result.inserted_id
        db["pending_channels"].insert_one({
            "channel_username": username, "channel_link": channel_link,
            "queued_at": now, "attempts": 0,
        })

    user_channels_col.insert_one({
        "user_id": user_id, "channel_username": username,
        "channel_link": channel_link, "subscribed_at": datetime.utcnow(),
    })

    ch_status = channel_doc.get("status", "pending")
    messages = {
        "pending": "Hệ thống đang tiến hành thu thập và sẽ cập nhật tóm tắt sớm nhất có thể.",
        "active": "Kênh đã có dữ liệu. Tóm tắt sẽ hiển thị ngay!",
    }
    return {
        "channel_link": channel_link, "username": username,
        "status": ch_status, "message": messages.get(ch_status, "Kênh đang được xử lý."),
    }


# ---------------------------------------------------------------------------
# Subscribe (single)
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def subscribe_channel(
    body: SubscribeChannelRequest,
    current_username: str = Depends(get_current_user),
):
    """Đăng ký một kênh Telegram để AI tóm tắt hàng ngày."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    result = _subscribe_one(db, user_id, body.channel_link)
    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail=result["message"])
    return result


# ---------------------------------------------------------------------------
# Bulk subscribe
# ---------------------------------------------------------------------------

@router.post("/bulk", status_code=200)
async def bulk_subscribe_channels(
    body: BulkSubscribeRequest,
    current_username: str = Depends(get_current_user),
):
    """
    Đăng ký nhiều kênh Telegram cùng lúc (tối đa 20 kênh).
    Trả về kết quả từng kênh — kênh lỗi không ảnh hưởng các kênh khác.
    """
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    results = []
    for raw_link in body.channel_links[:20]:
        if not raw_link.strip():
            continue
        try:
            r = _subscribe_one(db, user_id, raw_link.strip())
            results.append(r)
        except HTTPException as exc:
            results.append({
                "channel_link": raw_link.strip(), "username": None,
                "status": "error", "message": exc.detail,
            })

    added = sum(1 for r in results if r["status"] not in ("duplicate", "error"))
    skipped = sum(1 for r in results if r["status"] == "duplicate")
    errors = sum(1 for r in results if r["status"] == "error")

    return {
        "results": results,
        "summary": {"added": added, "skipped": skipped, "errors": errors},
    }


# ---------------------------------------------------------------------------
# List subscribed channels
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ChannelWithSummary])
async def list_subscribed_channels(
    current_username: str = Depends(get_current_user),
):
    """Lấy danh sách kênh đã đăng ký cùng bản tóm tắt mới nhất."""
    db = get_db()
    users_col = db["users"]
    user_channels_col = db["user_channels"]
    channels_col = db["channels"]
    summaries_col = db["channel_summaries"]

    user_doc = users_col.find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    subs = list(user_channels_col.find({"user_id": user_id}))
    if not subs:
        return []

    result = []
    for sub in subs:
        ch_username = sub["channel_username"]
        channel = channels_col.find_one({"username": ch_username}) or {}

        # Latest summary (sort by date desc)
        latest_summary = summaries_col.find_one(
            {"channel_username": ch_username},
            sort=[("date", -1)],
        )

        # Unread count: posts since user last viewed this channel
        last_seen_at = sub.get("last_seen_at")
        total_post_count = db["posts"].count_documents({"source": ch_username})
        if last_seen_at:
            unread_count = db["posts"].count_documents({
                "source": ch_username,
                "created_at": {"$gt": last_seen_at},
            })
        else:
            unread_count = total_post_count

        result.append(
            ChannelWithSummary(
                channel_link=sub.get("channel_link", normalize_link(ch_username)),
                username=ch_username,
                display_name=channel.get("display_name"),
                status=channel.get("status", "pending"),
                added_at=channel.get("added_at", sub["subscribed_at"]),
                post_count=total_post_count,
                latest_summary=latest_summary["summary_text"] if latest_summary else None,
                summary_date=latest_summary["date"] if latest_summary else None,
                subscribed_at=sub["subscribed_at"],
                unread_count=unread_count,
                error_message=channel.get("error_message"),
            )
        )

    result.sort(key=lambda c: c.subscribed_at, reverse=True)
    return result


# ---------------------------------------------------------------------------
# Unsubscribe
# ---------------------------------------------------------------------------

@router.delete("/{channel_username}", status_code=200)
async def unsubscribe_channel(
    channel_username: str,
    current_username: str = Depends(get_current_user),
):
    """Hủy đăng ký theo dõi kênh."""
    db = get_db()
    users_col = db["users"]
    user_channels_col = db["user_channels"]

    user_doc = users_col.find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    deleted = user_channels_col.delete_one({
        "user_id": user_id,
        "channel_username": channel_username.lstrip("@").lower(),
    })
    if deleted.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"message": "Đã hủy đăng ký kênh thành công."}


# ---------------------------------------------------------------------------
# Get channel summary (single channel)
# ---------------------------------------------------------------------------

@router.get("/{channel_username}/summary")
async def get_channel_summary(
    channel_username: str,
    current_username: str = Depends(get_current_user),
):
    """Lấy tóm tắt mới nhất của một kênh."""
    db = get_db()
    users_col = db["users"]
    user_channels_col = db["user_channels"]
    summaries_col = db["channel_summaries"]

    user_doc = users_col.find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    username = channel_username.lstrip("@").lower()

    # Ensure user is subscribed
    sub = user_channels_col.find_one({"user_id": user_id, "channel_username": username})
    if not sub:
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký kênh này.")

    summaries = list(
        summaries_col.find({"channel_username": username}).sort("date", -1).limit(7)
    )
    for s in summaries:
        s.pop("_id", None)

    return {"channel_username": username, "summaries": summaries}


# ---------------------------------------------------------------------------
# On-demand AI summary
# ---------------------------------------------------------------------------

async def _run_summarize(channel_username: str) -> None:
    """Background task: clean old posts → push channel to pending queue → worker re-fetches & summarizes.

    NOTE: We intentionally do NOT create a Telethon client here because the channel-queue
    worker already runs a managed session in the same process. Creating a second concurrent
    client on the same session file causes auth conflicts and failed fetches.
    """
    from src.ingestion.channel_queue_worker import FETCH_DAYS
    from datetime import timedelta
    db = get_db()
    try:
        # 1. Clean posts older than FETCH_DAYS
        cutoff = datetime.utcnow() - timedelta(days=FETCH_DAYS)
        deleted = db["posts"].delete_many({
            "source": channel_username,
            "created_at": {"$lt": cutoff},
        })
        if deleted.deleted_count:
            logger.info(f"Cleaned {deleted.deleted_count} old posts for @{channel_username}")

        # 2. Remove any existing summary so the frontend can detect when a new one arrives
        db["channel_summaries"].delete_many({"channel_username": channel_username})

        # 3. Push channel back into the pending queue — worker will re-fetch + re-summarize
        db["pending_channels"].update_one(
            {"channel_username": channel_username},
            {"$set": {
                "channel_username": channel_username,
                "attempts": 0,
                "next_attempt": datetime.utcnow(),
                "queued_at": datetime.utcnow(),
            }},
            upsert=True,
        )
        # Keep channel status as-is (active) — worker will update when done
        logger.info(f"@{channel_username} re-queued for fresh fetch + summary (worker will process)")
    except Exception as exc:
        logger.warning(f"Re-queue failed for @{channel_username}: {exc}")


@router.post("/{channel_username}/summarize", status_code=202)
async def trigger_summarize(
    channel_username: str,
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
):
    """Kích hoạt tạo tóm tắt AI cho kênh (chạy nền, ~5-10 giây)."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    username = channel_username.lstrip("@").lower()
    sub = db["user_channels"].find_one({"user_id": str(user_doc["_id"]), "channel_username": username})
    if not sub:
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký kênh này.")

    channel = db["channels"].find_one({"username": username}) or {}
    if channel.get("status") != "active":
        raise HTTPException(status_code=400, detail="Kênh chưa active — chờ hệ thống xử lý xong.")

    post_count = db["posts"].count_documents({"source": username})

    background_tasks.add_task(_run_summarize, username)
    return {"status": "generating", "message": "Đang xóa tin cũ, tải tin mới và tóm tắt AI — vui lòng chờ 15-30 giây."}


# ---------------------------------------------------------------------------
# Recent posts for a channel (with unread flag)
# ---------------------------------------------------------------------------

@router.get("/{channel_username}/posts")
async def get_channel_posts(
    channel_username: str,
    limit: int = Query(default=30, le=50),
    current_username: str = Depends(get_current_user),
):
    """Lấy tin mới nhất của kênh, tin chưa đọc (is_new=True) hiển thị trước."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    username = channel_username.lstrip("@").lower()
    sub = db["user_channels"].find_one({"user_id": user_id, "channel_username": username})
    if not sub:
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký kênh này.")

    last_seen_at = sub.get("last_seen_at")
    posts = list(
        db["posts"]
        .find({"source": username}, {"_id": 0, "id": 1, "text": 1, "links": 1, "created_at": 1, "topics": 1})
        .sort("created_at", -1)
        .limit(limit)
    )

    for p in posts:
        p["is_new"] = bool(last_seen_at is None or p.get("created_at", datetime.min) > last_seen_at)

    # Unread first, then by date
    posts.sort(key=lambda p: (not p["is_new"], -(p.get("created_at") or datetime.min).timestamp()))
    return posts


# ---------------------------------------------------------------------------
# Mark channel as seen (resets unread count)
# ---------------------------------------------------------------------------

@router.post("/{channel_username}/seen", status_code=200)
async def mark_channel_seen(
    channel_username: str,
    current_username: str = Depends(get_current_user),
):
    """Đánh dấu người dùng đã xem kênh — reset unread count về 0."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    username = channel_username.lstrip("@").lower()
    db["user_channels"].update_one(
        {"user_id": user_id, "channel_username": username},
        {"$set": {"last_seen_at": datetime.utcnow()}},
    )
    return {"message": "Đã cập nhật trạng thái đọc."}
