"""
Telegram Phone Login via MTProto (Telethon).

Luồng 3 bước:
  1. POST /auth/telegram/send-code   → Gửi OTP tới số điện thoại
  2. POST /auth/telegram/verify-code → Xác minh OTP, tạo session, tạo/đăng nhập user
  3. GET  /auth/telegram/channels    → Lấy danh sách kênh công khai (đã lọc privacy)
  4. POST /auth/telegram/select-channels → Lưu các kênh user chọn
"""
from __future__ import annotations

import asyncio
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    FloodWaitError,
)
from telethon.tl.types import Channel, Chat, User

from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from src.api.auth import (
    create_access_token,
    get_password_hash,
    get_current_user,
    get_current_user_token_data,
)
from src.db.mongo import get_db, get_users_collection

router = APIRouter(prefix="/auth/telegram", tags=["Telegram Phone Auth"])

# ---------------------------------------------------------------------------
# In-memory store for pending login sessions (phone_code_hash + TelegramClient)
# Key: session_id (random hex), Value: dict with client, phone, hash, timestamp
# Auto-cleanup entries older than 5 minutes
# ---------------------------------------------------------------------------
_pending_logins: dict[str, dict] = {}
_PENDING_TTL = 300  # 5 minutes


def _cleanup_pending():
    """Remove expired pending login sessions."""
    now = time.time()
    expired = [k for k, v in _pending_logins.items() if now - v["created_at"] > _PENDING_TTL]
    for k in expired:
        client = _pending_logins[k].get("client")
        if client and client.is_connected():
            asyncio.create_task(client.disconnect())
        del _pending_logins[k]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CheckPhoneResponse(BaseModel):
    exists: bool
    display_name: Optional[str] = None


class SendCodeRequest(BaseModel):
    phone_number: str = Field(..., min_length=8, max_length=20, description="Số điện thoại quốc tế, VD: +84912345678")
    display_name: Optional[str] = Field(None, max_length=100, description="Tên hiển thị — chỉ cần thiết với user mới")


class SendCodeResponse(BaseModel):
    session_id: str
    phone_code_hash: str
    message: str


class VerifyCodeRequest(BaseModel):
    session_id: str
    phone_number: str
    phone_code_hash: str
    code: str = Field(..., min_length=4, max_length=8, description="Mã OTP từ Telegram")
    password: Optional[str] = Field(None, description="Mật khẩu 2FA (nếu bật)")


class VerifyCodeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
    role: str
    full_name: Optional[str] = None
    phone_number: str
    is_new_user: bool = False
    has_channels: bool = False


class TelegramChannelItem(BaseModel):
    id: str
    name: str
    username: Optional[str] = None
    is_public: bool
    is_megagroup: bool
    member_count: Optional[int] = None


class SelectChannelsRequest(BaseModel):
    channel_ids: list[str] = Field(
        ..., min_length=1, max_length=50,
        description="Danh sách ID kênh Telegram đã chọn",
    )


# ---------------------------------------------------------------------------
# 0. Check phone (returning user detection)
# ---------------------------------------------------------------------------

@router.get("/check-phone", response_model=CheckPhoneResponse)
async def check_phone(phone: str):
    """
    Kiểm tra số điện thoại đã đăng ký chưa.
    Frontend dùng để ẩn field tên nếu là user cũ.
    """
    if not phone.strip():
        raise HTTPException(status_code=422, detail="Số điện thoại không hợp lệ")
    users_col = get_users_collection()
    user_doc = users_col.find_one({"phone_number": phone.strip()}, {"full_name": 1})
    if user_doc:
        return CheckPhoneResponse(exists=True, display_name=user_doc.get("full_name"))
    return CheckPhoneResponse(exists=False)


# ---------------------------------------------------------------------------
# 1. Send OTP Code
# ---------------------------------------------------------------------------

@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(body: SendCodeRequest):
    """
    Bước 1: Gửi mã OTP đến số điện thoại Telegram.
    Trả về session_id và phone_code_hash để dùng ở bước 2.
    """
    _cleanup_pending()

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Telegram API chưa được cấu hình (thiếu API_ID/API_HASH).",
        )

    phone = body.phone_number.strip()
    display_name = (body.display_name or "").strip()

    # Rate limit: max 1 pending per phone number
    for v in _pending_logins.values():
        if v["phone"] == phone:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Đã gửi mã OTP cho số này. Vui lòng chờ 5 phút trước khi thử lại.",
            )

    client = TelegramClient(
        StringSession(), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )

    try:
        await client.connect()
        result = await client.send_code_request(phone)
    except PhoneNumberInvalidError:
        await client.disconnect()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Số điện thoại không hợp lệ. Sử dụng định dạng quốc tế, VD: +84912345678",
        )
    except FloodWaitError as e:
        await client.disconnect()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Telegram yêu cầu chờ {e.seconds} giây trước khi thử lại.",
        )
    except Exception as e:
        await client.disconnect()
        logger.error(f"Telegram send-code error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không thể gửi mã OTP: {str(e)}",
        )

    session_id = secrets.token_hex(16)
    _pending_logins[session_id] = {
        "client": client,
        "phone": phone,
        "phone_code_hash": result.phone_code_hash,
        "display_name": display_name,
        "created_at": time.time(),
    }

    logger.info(f"Telegram OTP sent to {phone[:6]}***")
    return SendCodeResponse(
        session_id=session_id,
        phone_code_hash=result.phone_code_hash,
        message="Mã OTP đã được gửi qua Telegram. Hãy kiểm tra ứng dụng Telegram.",
    )


# ---------------------------------------------------------------------------
# 2. Verify OTP & Create/Login User
# ---------------------------------------------------------------------------

@router.post("/verify-code", response_model=VerifyCodeResponse)
async def verify_code(body: VerifyCodeRequest):
    """
    Bước 2: Xác minh OTP.
    Tạo tài khoản mới hoặc đăng nhập nếu số điện thoại đã tồn tại.
    Lưu Telegram session string vào DB.
    """
    pending = _pending_logins.get(body.session_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phiên đăng nhập không tồn tại hoặc đã hết hạn. Vui lòng gửi lại mã OTP.",
        )

    client: TelegramClient = pending["client"]
    phone = pending["phone"]
    display_name = pending["display_name"]

    if body.phone_number.strip() != phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số điện thoại không khớp với phiên đăng nhập.",
        )

    try:
        await client.sign_in(
            phone=phone,
            code=body.code.strip(),
            phone_code_hash=body.phone_code_hash,
        )
    except PhoneCodeInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã OTP không đúng. Vui lòng kiểm tra lại.",
        )
    except PhoneCodeExpiredError:
        # Clean up
        del _pending_logins[body.session_id]
        await client.disconnect()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Mã OTP đã hết hạn. Vui lòng gửi lại mã mới.",
        )
    except SessionPasswordNeededError:
        # Two-factor authentication required
        if not body.password:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail="Tài khoản Telegram bật xác thực 2 lớp. Vui lòng nhập mật khẩu 2FA.",
            )
        try:
            await client.sign_in(password=body.password)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Mật khẩu 2FA không đúng: {str(e)}",
            )
    except FloodWaitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quá nhiều lần thử. Chờ {e.seconds} giây.",
        )
    except Exception as e:
        logger.error(f"Telegram verify error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lỗi xác minh: {str(e)}",
        )

    # Get Telegram user info
    me = await client.get_me()
    telegram_user_id = str(me.id)
    telegram_username = me.username or ""

    # Save session string
    session_string = client.session.save()

    # Disconnect and remove from pending
    del _pending_logins[body.session_id]
    # Keep client connected? No — we save session string for later use
    await client.disconnect()

    # Create or update user in MongoDB
    users_col = get_users_collection()
    db = get_db()

    # Look up user by phone number
    user_doc = users_col.find_one({"phone_number": phone})

    if user_doc is None:
        # Also check by telegram_user_id
        user_doc = users_col.find_one({"telegram_user_id": telegram_user_id})

    is_new_user = user_doc is None

    if is_new_user:
        # Create new user
        username_base = (telegram_username or f"tg_{telegram_user_id}")[:28]
        username = username_base
        suffix = 1
        while users_col.find_one({"username": username}):
            username = f"{username_base}_{suffix}"
            suffix += 1

        user_doc = {
            "username": username,
            "full_name": display_name or telegram_username or username,
            "phone_number": phone,
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "telegram_session": session_string,
            "password_hash": get_password_hash(secrets.token_hex(32)),
            "role": "user",
            "status": "active",
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
        }
        users_col.insert_one(user_doc)
        logger.info(f"New Telegram user registered: {username} ({phone[:6]}***)")        
    else:
        # Update existing user — KHÔNG ghi đè full_name nếu user không nhập
        username = user_doc["username"]
        update_fields = {
            "telegram_session": session_string,
            "telegram_user_id": telegram_user_id,
            "last_login": datetime.utcnow(),
        }
        if display_name:  # chỉ cập nhật khi user chủ động nhập
            update_fields["full_name"] = display_name
        if telegram_username:
            update_fields["telegram_username"] = telegram_username
        users_col.update_one({"_id": user_doc["_id"]}, {"$set": update_fields})
        logger.info(f"Telegram returning user login: {username} ({phone[:6]}***)")        

    # Check if user already has subscribed channels
    db_ref = get_db()
    channel_count = db_ref["user_channels"].count_documents({"user_id": str(user_doc.get("_id", ""))})
    has_channels = channel_count > 0

    role = user_doc.get("role", "user")
    access_token = create_access_token(
        {"sub": username, "role": role},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    final_full_name = display_name or user_doc.get("full_name") or username
    return VerifyCodeResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        username=username,
        role=role,
        full_name=final_full_name,
        phone_number=phone,
        is_new_user=is_new_user,
        has_channels=has_channels,
    )


# ---------------------------------------------------------------------------
# 3. Get Public Channels (Privacy Filter)
# ---------------------------------------------------------------------------

@router.get("/channels", response_model=list[TelegramChannelItem])
async def get_telegram_channels(
    current_username: str = Depends(get_current_user),
):
    """
    Bước 3: Quét và lọc các kênh Telegram công khai mà user đang theo dõi.

    BỘ LỌC QUYỀN RIÊNG TƯ (Privacy Filter):
    - BỎ QUA: User (Chat cá nhân 1-1)
    - BỎ QUA: Chat (Nhóm nhỏ cá nhân/gia đình)
    - CHỈ LẤY: Channel (broadcast) hoặc Megagroup (nhóm công khai lớn)
    """
    users_col = get_users_collection()
    user_doc = users_col.find_one({"username": current_username})

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    session_string = user_doc.get("telegram_session")
    if not session_string:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Chưa liên kết Telegram. Vui lòng đăng nhập bằng số điện thoại trước.",
        )

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Telegram API chưa được cấu hình.",
        )

    client = TelegramClient(
        StringSession(session_string), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên Telegram đã hết hạn. Vui lòng đăng nhập lại.",
            )

        dialogs = await client.get_dialogs()
        allowed_channels: list[TelegramChannelItem] = []

        for dialog in dialogs:
            entity = dialog.entity

            # ─── BỘ LỌC QUYỀN RIÊNG TƯ ───────────────────────
            # 1. User (Chat cá nhân 1-1) → BỎ QUA NGAY LẬP TỨC
            if isinstance(entity, User):
                continue

            # 2. Chat (Group nhỏ cá nhân/gia đình) → BỎ QUA
            if isinstance(entity, Chat):
                continue

            # 3. Channel (Kênh broadcast hoặc Megagroup) → KIỂM TRA TIẾP
            if isinstance(entity, Channel):
                # Chỉ lấy broadcast (kênh phát sóng) hoặc megagroup (nhóm công khai lớn)
                if entity.broadcast or entity.megagroup:
                    allowed_channels.append(
                        TelegramChannelItem(
                            id=str(entity.id),
                            name=entity.title or "Unknown",
                            username=entity.username or None,
                            is_public=bool(entity.username),
                            is_megagroup=bool(entity.megagroup),
                            member_count=getattr(entity, "participants_count", None),
                        )
                    )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Telegram channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Không thể lấy danh sách kênh: {str(e)}",
        )
    finally:
        await client.disconnect()

    logger.info(f"User {current_username}: found {len(allowed_channels)} public channels")
    return allowed_channels


# ---------------------------------------------------------------------------
# 4. Select Channels to Subscribe
# ---------------------------------------------------------------------------

@router.post("/select-channels", status_code=201)
async def select_channels(
    body: SelectChannelsRequest,
    current_username: str = Depends(get_current_user),
):
    """
    Bước 4: User chọn các kênh muốn AI tóm tắt.
    Hệ thống lưu vào user_channels và bắt đầu cào tin.
    """
    users_col = get_users_collection()
    db = get_db()
    user_doc = users_col.find_one({"username": current_username})

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user_doc["_id"])
    session_string = user_doc.get("telegram_session")

    if not session_string:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Chưa liên kết Telegram.",
        )

    # Re-connect to get channel info for the selected IDs
    client = TelegramClient(
        StringSession(session_string), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    )

    channels_col = db["channels"]
    user_channels_col = db["user_channels"]
    pending_col = db["pending_channels"]

    results = []

    try:
        await client.connect()

        if not await client.is_user_authorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên Telegram đã hết hạn.",
            )

        dialogs = await client.get_dialogs()

        # Build a lookup of allowed channels by ID
        channel_map: dict[str, Channel] = {}
        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel) and (entity.broadcast or entity.megagroup):
                channel_map[str(entity.id)] = entity

        for ch_id in body.channel_ids:
            entity = channel_map.get(ch_id)
            if not entity:
                results.append({"id": ch_id, "status": "skipped", "message": "Kênh không tìm thấy hoặc không hợp lệ."})
                continue

            # Use channel username for Telegram channels, or ID-based name for private channels
            ch_username = (entity.username or f"tg_id_{entity.id}").lower()
            ch_link = f"t.me/{entity.username}" if entity.username else f"tg://channel?id={entity.id}"
            ch_display_name = entity.title or ch_username

            # Check if already subscribed
            if user_channels_col.find_one({"user_id": user_id, "channel_username": ch_username}):
                results.append({"id": ch_id, "username": ch_username, "status": "duplicate", "message": "Đã đăng ký."})
                continue

            # Create or find channel doc
            now = datetime.utcnow()
            channel_doc = channels_col.find_one({"username": ch_username})
            if channel_doc is None:
                channel_doc = {
                    "channel_link": ch_link,
                    "username": ch_username,
                    "display_name": ch_display_name,
                    "platform": "telegram",
                    "status": "pending",
                    "added_at": now,
                    "processed_at": None,
                    "error_message": None,
                    "post_count": 0,
                }
                channels_col.insert_one(channel_doc)
                # Queue for background processing
                pending_col.insert_one({
                    "channel_username": ch_username,
                    "channel_link": ch_link,
                    "queued_at": now,
                    "attempts": 0,
                })

            # Subscribe user
            user_channels_col.insert_one({
                "user_id": user_id,
                "channel_username": ch_username,
                "channel_link": ch_link,
                "subscribed_at": now,
            })

            results.append({
                "id": ch_id,
                "username": ch_username,
                "display_name": ch_display_name,
                "status": "subscribed",
                "message": "Đã đăng ký! Hệ thống sẽ bắt đầu thu thập và tóm tắt.",
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Lỗi khi đăng ký kênh: {str(e)}",
        )
    finally:
        await client.disconnect()

    added = sum(1 for r in results if r["status"] == "subscribed")
    skipped = sum(1 for r in results if r["status"] == "duplicate")

    logger.info(f"User {current_username}: selected {added} channels, {skipped} duplicates")
    return {
        "results": results,
        "summary": {"added": added, "skipped": skipped, "total": len(body.channel_ids)},
    }


# ---------------------------------------------------------------------------
# Profile: Get user info with Telegram link status
# ---------------------------------------------------------------------------

@router.get("/profile")
async def get_telegram_profile(
    current_username: str = Depends(get_current_user),
):
    """Lấy thông tin profile user bao gồm trạng thái liên kết Telegram."""
    users_col = get_users_collection()
    user_doc = users_col.find_one({"username": current_username})

    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user_doc.get("username"),
        "full_name": user_doc.get("full_name"),
        "email": user_doc.get("email"),
        "phone_number": user_doc.get("phone_number"),
        "telegram_username": user_doc.get("telegram_username"),
        "telegram_linked": bool(user_doc.get("telegram_session")),
        "role": user_doc.get("role", "user"),
        "status": user_doc.get("status", "active"),
        "created_at": user_doc.get("created_at"),
        "last_login": user_doc.get("last_login"),
    }
