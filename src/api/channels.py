"""Channel subscription API endpoints."""
from __future__ import annotations
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from src.api.auth import get_current_user
from src.db.mongo import get_db
from src.models.channel import SubscribeChannelRequest, BulkSubscribeRequest, ChannelWithSummary

router = APIRouter(prefix="/user/channels", tags=["Channel Subscriptions"])

# Minimum hours between Apify fetches for the same X channel/keyword
_APIFY_COOLDOWN_HRS = 6

# Path to the channel catalog JSON (relative to project root)
_CATALOG_PATH = Path(__file__).resolve().parents[2] / "channel.json"

# Cache the catalog in-memory (loaded once, never changes at runtime)
_catalog_cache: list[dict] | None = None


def _load_catalog() -> list[dict]:
    global _catalog_cache
    if _catalog_cache is None:
        try:
            _catalog_cache = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            _catalog_cache = []
    return _catalog_cache


# ---------------------------------------------------------------------------
# Background task: trigger channel_queue_worker cho kênh mới
# ---------------------------------------------------------------------------

async def _trigger_channel_processing(username: str) -> None:
    """
    Bước 3 — Trigger Worker:
    Chạy process kênh mới ngay trong background khi user subscribe,
    thay vì chờ poll 30 giây của channel_queue_worker.
    
    Với X/Twitter: cào tweet ngay qua Apify.
    Với Telegram  : đẩy vào pending_channels (worker tự poll).
    """
    db = get_db()
    channels_col = db["channels"]

    def _mark_active(uname: str, post_count: int = 0) -> None:
        channels_col.update_one(
            {"username": uname},
            {"$set": {
                "status": "active",
                "processed_at": __import__("datetime").datetime.utcnow(),
                "error_message": None,
                "post_count": post_count,
            }},
        )

    def _mark_error(uname: str, msg: str) -> None:
        channels_col.update_one(
            {"username": uname},
            {"$set": {"status": "error", "error_message": msg}},
        )

    try:
        # Guard: nếu channel đã bị xóa (user unsubscribe trước khi task chạy) thì bỏ qua
        if not channels_col.find_one({"username": username}, {"_id": 1}):
            logger.info(f"[Subscribe-Trigger] '{username}' không còn trong DB — bỏ qua")
            return

        if username.startswith("xkw:"):         # X keyword / hashtag search
            kw = username[4:]
            from src.ingestion.x_worker import ingest_once
            from src.ingestion.channel_queue_worker import _generate_summary, _save_summary
            # Cooldown: skip Apify if same keyword was fetched within _APIFY_COOLDOWN_HRS
            channel_doc = channels_col.find_one({"username": username}, {"last_apify_fetch": 1})
            last_fetch = (channel_doc or {}).get("last_apify_fetch")
            if last_fetch and (datetime.utcnow() - last_fetch) < timedelta(hours=_APIFY_COOLDOWN_HRS):
                logger.info(f"[Subscribe-Trigger] xkw:{kw} — cooldown aktif (last fetch {last_fetch}), bỏ qua Apify")
                total = db["posts"].count_documents({"platform": "twitter", "$text": {"$search": kw}})
                _mark_active(username, total)
                return
            logger.info(f"[Subscribe-Trigger] Bắt đầu cào X keyword: #{kw}")
            saved = await ingest_once(mode="keyword", keywords=[kw], max_items=20)
            channels_col.update_one({"username": username}, {"$set": {"last_apify_fetch": datetime.utcnow()}})
            total = db["posts"].count_documents({"platform": "twitter", "$text": {"$search": kw}})
            _mark_active(username, total)
            logger.info(f"[Subscribe-Trigger] xkw:{kw} → active ({total} posts)")
            # Generate AI summary
            summary = await _generate_summary(username, db)
            if summary:
                _save_summary(username, summary, total, db)
                logger.info(f"[Subscribe-Trigger] xkw:{kw} summary saved")
        elif username.startswith("x:"):         # X/Twitter account
            real_username = username[2:]        # bỏ prefix "x:"
            from src.ingestion.x_worker import ingest_once
            from src.ingestion.channel_queue_worker import _generate_summary, _save_summary
            # Cooldown: skip Apify if same account was fetched within _APIFY_COOLDOWN_HRS
            channel_doc = channels_col.find_one({"username": username}, {"last_apify_fetch": 1})
            last_fetch = (channel_doc or {}).get("last_apify_fetch")
            if last_fetch and (datetime.utcnow() - last_fetch) < timedelta(hours=_APIFY_COOLDOWN_HRS):
                logger.info(f"[Subscribe-Trigger] x:{real_username} — cooldown aktif, bỏ qua Apify")
                total = db["posts"].count_documents({"source": username})
                _mark_active(username, total)
                return
            logger.info(f"[Subscribe-Trigger] Bắt đầu cào X account: @{real_username}")
            saved = await ingest_once(mode="user", usernames=[real_username], max_items=20)
            channels_col.update_one({"username": username}, {"$set": {"last_apify_fetch": datetime.utcnow()}})
            total = db["posts"].count_documents({"source": username})
            _mark_active(username, total)
            logger.info(f"[Subscribe-Trigger] x:{real_username} → active ({total} posts)")
            # Generate AI summary
            summary = await _generate_summary(username, db)
            if summary:
                _save_summary(username, summary, total, db)
                logger.info(f"[Subscribe-Trigger] x:{real_username} summary saved")
        else:                                   # Telegram channel
            # channel_queue_worker.py đang poll pending_channels rồi
            # — chỉ log, không cần làm gì thêm
            logger.info(f"[Subscribe-Trigger] Kênh Telegram '{username}' đã vào pending_channels, worker sẽ xử lý trong <30 giây")
    except Exception as e:
        # Không được raise trong background task — chỉ log
        logger.error(f"[Subscribe-Trigger] Lỗi khi trigger worker cho '{username}': {e}")
        if username.startswith(("x:", "xkw:")):
            _mark_error(username, str(e))

# ---------------------------------------------------------------------------
# Catalog: all 106 curated channels from channel.json, grouped by category
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def get_channel_catalog(current_username: str = Depends(get_current_user)):
    """Trả về toàn bộ danh mục kênh gợi ý (từ channel.json), nhóm theo category."""
    db = get_db()

    # Load catalog (cached in memory)
    catalog = _load_catalog()
    if not catalog:
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

    # Batch count posts using aggregation instead of N+1 queries
    all_usernames = [ch["username"] for ch in channels]
    post_count_map = {}
    if all_usernames:
        for doc in db["posts"].aggregate([
            {"$match": {"source": {"$in": all_usernames}}},
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        ]):
            post_count_map[doc["_id"]] = doc["count"]

    for ch in channels:
        ch["post_count"] = post_count_map.get(ch["username"], 0)

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

# x.com/user  hoặc  twitter.com/user
_XLINK_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,50})",
    re.IGNORECASE,
)

# #hashtag hoặc x:#hashtag  →  X keyword search
_XHASHTAG_RE = re.compile(r"^(?:x:)?#(\S+)$", re.IGNORECASE)


def parse_channel_input(raw: str) -> tuple[str, str]:
    """
    Parse input từ user, trả về (username, platform).

    Input hỗ trợ:
      Telegram : t.me/vnexpress  |  @vnexpress  |  vnexpress
      X user   : x.com/TechCrunch  |  twitter.com/TechCrunch
      X keyword: #bitcoin  |  #AI  |  x:#ReactJS

    Phân biệt nội bộ:
      - Telegram username lưu thẳng ("vnexpress")
      - X user    lưu với prefix "x:"   ("x:TechCrunch")
      - X keyword lưu với prefix "xkw:" ("xkw:bitcoin")
    """
    raw = raw.strip()

    # X hashtag / keyword search  (#bitcoin, x:#AI)
    mh = _XHASHTAG_RE.match(raw)
    if mh:
        kw = mh.group(1)
        return f"xkw:{kw}", "twitter"

    # X / Twitter user link
    mx = _XLINK_RE.match(raw)
    if mx:
        username = mx.group(1).lstrip("@")
        return f"x:{username}", "twitter"

    # Telegram link / @handle / plain username
    mt = _TGLINK_RE.match(raw)
    if mt:
        username = (mt.group(1) or mt.group(2) or mt.group(3)).lstrip("@").lower()
        return username, "telegram"

    raise HTTPException(
        status_code=422,
        detail="Link không hợp lệ. Dùng: t.me/ten_kenh, @ten_kenh, x.com/user, twitter.com/user, hoặc #hashtag",
    )


def parse_channel_username(raw: str) -> str:
    """Backward-compatible wrapper — chỉ dùng cho Telegram."""
    username, _ = parse_channel_input(raw)
    return username


def _normalize_username(raw: str) -> str:
    """Normalize channel username for DB lookup.
    Telegram: lowercase. x:/xkw: prefixes: preserve original case.
    """
    s = raw.lstrip("@")
    if s.startswith(("x:", "xkw:")):
        return s
    return s.lower()


def normalize_link(username: str) -> str:
    """Tạo display link từ username (có prefix x:, xkw: hoặc không)."""
    if username.startswith("xkw:"):
        from urllib.parse import quote
        return f"x.com/search?q={quote('#' + username[4:])}"
    if username.startswith("x:"):
        return f"x.com/{username[2:]}"
    return f"t.me/{username}"


def _subscribe_one(db, user_id: str, raw_link: str) -> dict:
    """
    Core subscribe logic (Bước 1 + 2). Returns a result dict with status/message.
    Raises HTTPException on hard errors (bad link format, DB errors).
    Returns {"status": "duplicate"} if already subscribed (soft skip).

    Bước 1 — De-duplication: kiểm tra kênh đã có trong DB chưa.
    Bước 2 — Subscription: lưu quan hệ user ↔ channel vào user_channels.
    (Bước 3 — Trigger Worker: do endpoint gọi _trigger_channel_processing qua BackgroundTasks)
    """
    channels_col = db["channels"]
    user_channels_col = db["user_channels"]

    # parse — tự nhận diện Telegram hay X
    username, platform = parse_channel_input(raw_link)
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
            "platform": platform,                # "telegram" hoặc "twitter"
            "display_name": None, "status": "pending",
            "added_at": now, "processed_at": None,
            "error_message": None, "post_count": 0,
        }
        result = channels_col.insert_one(channel_doc)
        channel_doc["_id"] = result.inserted_id
        # Telegram cần queue riêng; X sẽ được trigger trực tiếp qua BackgroundTasks
        if platform == "telegram":
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
    background_tasks: BackgroundTasks,
    current_username: str = Depends(get_current_user),
):
    """Đăng ký một kênh Telegram/X để AI tóm tắt hàng ngày."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    result = _subscribe_one(db, user_id, body.channel_link)
    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail=result["message"])

    # Bước 3 — Trigger Worker ngay nếu là nguồn mới hoàn toàn
    if result["status"] == "pending":
        background_tasks.add_task(_trigger_channel_processing, result["username"])
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

    # Batch-fetch all channels and summaries at once (avoid N+1)
    ch_usernames = [sub["channel_username"] for sub in subs]

    channels_map = {
        c["username"]: c
        for c in channels_col.find({"username": {"$in": ch_usernames}})
    }

    # Latest summary per channel (sort by date desc, take first per channel)
    summaries_map = {}
    for s in summaries_col.find(
        {"channel_username": {"$in": ch_usernames}}
    ).sort("date", -1):
        summaries_map.setdefault(s["channel_username"], s)

    # Batch count posts per source using aggregation
    normal_usernames = [u for u in ch_usernames if not u.startswith("xkw:")]
    xkw_usernames = [u for u in ch_usernames if u.startswith("xkw:")]

    post_counts = {}
    if normal_usernames:
        for doc in db["posts"].aggregate([
            {"$match": {"source": {"$in": normal_usernames}}},
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        ]):
            post_counts[doc["_id"]] = doc["count"]

    # Batch xkw: counts using $text search (single pipeline for all keywords)
    xkw_post_counts = {}
    xkw_unread_counts = {}
    if xkw_usernames:
        # Use $text search for each keyword batch
        xkw_or_filters = []
        for u in xkw_usernames:
            kw = u[4:]
            xkw_or_filters.append({"text": {"$regex": re.escape(kw), "$options": "i"}})
        
        # Get counts per keyword via aggregation
        for u in xkw_usernames:
            kw = u[4:]
            # Use a single estimated count from the channel doc if available
            ch_doc = channels_map.get(u, {})
            xkw_post_counts[u] = ch_doc.get("post_count", 0)

    # Batch unread counts using aggregation
    unread_counts = {}
    # Build per-channel filters for unread
    seen_map = {sub["channel_username"]: sub.get("last_seen_at") for sub in subs}

    # For normal channels with last_seen_at, batch count unread
    unread_filters = []
    for u in normal_usernames:
        last_seen = seen_map.get(u)
        if last_seen:
            unread_filters.append(u)
    if unread_filters:
        # Get unread posts per channel in one pipeline
        for doc in db["posts"].aggregate([
            {"$match": {"$or": [
                {"source": u, "created_at": {"$gt": seen_map[u]}}
                for u in unread_filters
            ]}},
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        ]):
            unread_counts[doc["_id"]] = doc["count"]

    result = []
    for sub in subs:
        ch_username = sub["channel_username"]
        channel = channels_map.get(ch_username, {})
        latest_summary = summaries_map.get(ch_username)
        last_seen_at = sub.get("last_seen_at")

        # xkw: channels — use cached count from channels doc
        if ch_username.startswith("xkw:"):
            total_post_count = xkw_post_counts.get(ch_username, 0)
            # Estimate unread as total if never seen, else 0 (avoid expensive regex count)
            unread_count = total_post_count if not last_seen_at else 0
        else:
            total_post_count = post_counts.get(ch_username, 0)
            if last_seen_at:
                unread_count = unread_counts.get(ch_username, 0)
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

    # Telegram usernames are stored lowercase; x:/xkw: prefixes preserve original case
    raw = channel_username.lstrip("@")
    if not raw.startswith(("x:", "xkw:")):
        raw = raw.lower()

    deleted = user_channels_col.delete_one({
        "user_id": user_id,
        "channel_username": raw,
    })
    if deleted.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Nếu không còn user nào subscribe → dọn channel khỏi DB
    remaining = user_channels_col.count_documents({"channel_username": raw})
    if remaining == 0:
        db["channels"].delete_one({"username": raw})
        db["channel_summaries"].delete_many({"channel_username": raw})
        db["pending_channels"].delete_many({"channel_username": raw})

        # x:username → xóa posts (posts có source = "x:username" rõ ràng)
        if raw.startswith("x:"):
            result = db["posts"].delete_many({"source": raw})
            logger.info(f"[Unsubscribe] x: {raw} — xóa {result.deleted_count} posts")
        # xkw:keyword → KHÔNG xóa posts vì posts thuộc nhiều author khác nhau
        elif raw.startswith("xkw:"):
            logger.info(f"[Unsubscribe] xkw: {raw} — channel đã xóa, posts giữ nguyên")
        else:
            # Telegram: xóa posts theo source
            result = db["posts"].delete_many({"source": raw})
            logger.info(f"[Unsubscribe] @{raw} — xóa {result.deleted_count} posts")

        logger.info(f"[Unsubscribe] '{raw}' không còn subscriber — đã xóa khỏi DB")

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

    username = _normalize_username(channel_username)

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
    """Background task: re-fetch and regenerate AI summary for a channel.

    - Telegram : push to pending_channels (worker re-fetches via Telethon)
    - X user/keyword : directly re-ingest via x_worker then summarize
    """
    from src.ingestion.channel_queue_worker import FETCH_DAYS, _generate_summary, _save_summary
    from datetime import timedelta
    db = get_db()

    # Remove any existing summary so the frontend can detect when a new one arrives
    db["channel_summaries"].delete_many({"channel_username": channel_username})

    try:
        if channel_username.startswith("xkw:"):
            kw = channel_username[4:]
            from src.ingestion.x_worker import ingest_once
            logger.info(f"[Summarize] Re-fetching X keyword: #{kw}")
            await ingest_once(mode="keyword", keywords=[kw], max_items=50)
            db["channels"].update_one({"username": channel_username}, {"$set": {"last_apify_fetch": datetime.utcnow()}})
            total = db["posts"].count_documents({"platform": "twitter", "$text": {"$search": kw}})
            summary = await _generate_summary(channel_username, db)
            if summary:
                _save_summary(channel_username, summary, total, db)
                db["channels"].update_one(
                    {"username": channel_username},
                    {"$set": {"post_count": total, "status": "active"}},
                )
                logger.info(f"[Summarize] xkw:{kw} summary saved ({total} posts)")

        elif channel_username.startswith("x:"):
            real_username = channel_username[2:]
            from src.ingestion.x_worker import ingest_once
            logger.info(f"[Summarize] Re-fetching X account: @{real_username}")
            await ingest_once(mode="user", usernames=[real_username], max_items=50)
            db["channels"].update_one({"username": channel_username}, {"$set": {"last_apify_fetch": datetime.utcnow()}})
            total = db["posts"].count_documents({"source": channel_username})
            summary = await _generate_summary(channel_username, db)
            if summary:
                _save_summary(channel_username, summary, total, db)
                db["channels"].update_one(
                    {"username": channel_username},
                    {"$set": {"post_count": total, "status": "active"}},
                )
                logger.info(f"[Summarize] x:{real_username} summary saved ({total} posts)")

        else:
            # Telegram: clean old posts then push to pending queue
            cutoff = datetime.utcnow() - timedelta(days=FETCH_DAYS)
            deleted = db["posts"].delete_many({
                "source": channel_username,
                "created_at": {"$lt": cutoff},
            })
            if deleted.deleted_count:
                logger.info(f"Cleaned {deleted.deleted_count} old posts for @{channel_username}")

            # Push channel back into the pending queue — worker will re-fetch + re-summarize
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
            logger.info(f"@{channel_username} re-queued for fresh fetch + summary (worker will process)")

    except Exception as exc:
        logger.warning(f"Re-summarize failed for @{channel_username}: {exc}")


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

    username = _normalize_username(channel_username)
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
    limit: int = Query(default=30, le=100),
    hours: int = Query(default=24, ge=1, le=168),  # 1h – 7 days; default 24h
    current_username: str = Depends(get_current_user),
):
    """Lấy tin mới nhất của kênh trong `hours` giờ gần nhất.
    Tin chưa đọc (is_new=True) hiển thị trước."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])

    username = _normalize_username(channel_username)
    sub = db["user_channels"].find_one({"user_id": user_id, "channel_username": username})
    if not sub:
        raise HTTPException(status_code=403, detail="Bạn chưa đăng ký kênh này.")

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    last_seen_at = sub.get("last_seen_at")

    # xkw: channels: posts stored with source="x:author", match by keyword text
    if username.startswith("xkw:"):
        import re as _re
        kw = username[4:]
        _posts_query: dict = {
            "platform": "twitter",
            "text": {"$regex": _re.escape(kw), "$options": "i"},
            "created_at": {"$gte": cutoff},
        }
    else:
        _posts_query = {"source": username, "created_at": {"$gte": cutoff}}

    posts = list(
        db["posts"]
        .find(
            _posts_query,
            {"_id": 0, "id": 1, "text": 1, "links": 1, "created_at": 1, "topics": 1},
        )
        .sort("created_at", -1)
        .limit(limit)
    )

    read_post_ids = set(sub.get("read_post_ids", []))
    _epoch = datetime(1970, 1, 1)
    for p in posts:
        ca = p.get("created_at")
        # Strip tzinfo if present (MongoDB may return aware datetimes)
        if ca and hasattr(ca, "tzinfo") and ca.tzinfo is not None:
            ca = ca.replace(tzinfo=None)
            p["created_at"] = ca
        ls = last_seen_at
        if ls and hasattr(ls, "tzinfo") and ls.tzinfo is not None:
            ls = ls.replace(tzinfo=None)
        p["is_new"] = bool(ls is None or (ca or _epoch) > ls)
        p["is_read"] = p.get("id") in read_post_ids

    # Unread+new first → unread+old → read last, then by date desc
    posts.sort(key=lambda p: (
        p.get("is_read", False),          # read posts sink to bottom
        not p["is_new"],                  # new (unread) before old (unread)
        -(((p.get("created_at") or _epoch) - _epoch).total_seconds()),
    ))
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

    username = _normalize_username(channel_username)
    db["user_channels"].update_one(
        {"user_id": user_id, "channel_username": username},
        {"$set": {"last_seen_at": datetime.utcnow()}},
    )
    return {"message": "Đã cập nhật trạng thái đọc."}


# ---------------------------------------------------------------------------
# Mark a single post as read (real-time read tracking)
# ---------------------------------------------------------------------------

@router.post("/{channel_username}/posts/{post_id:path}/read", status_code=200)
async def mark_post_read(
    channel_username: str,
    post_id: str,
    current_username: str = Depends(get_current_user),
):
    """Đánh dấu 1 bài đã đọc — lưu vào user_channels.read_post_ids."""
    db = get_db()
    user_doc = db["users"].find_one({"username": current_username})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_id = str(user_doc["_id"])
    username = _normalize_username(channel_username)

    # Add post_id to set
    db["user_channels"].update_one(
        {"user_id": user_id, "channel_username": username},
        {"$addToSet": {"read_post_ids": post_id}},
    )
    # Cap at 500 most-recent to prevent unbounded growth
    sub = db["user_channels"].find_one(
        {"user_id": user_id, "channel_username": username},
        {"read_post_ids": 1},
    )
    if sub and len(sub.get("read_post_ids", [])) > 500:
        db["user_channels"].update_one(
            {"user_id": user_id, "channel_username": username},
            {"$set": {"read_post_ids": sub["read_post_ids"][-500:]}},
        )
    return {"ok": True}
