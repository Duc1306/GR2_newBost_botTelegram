"""Authentication routes: login, register, logout, me, Google OAuth."""
from __future__ import annotations
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from src.db.mongo import get_db, get_users_collection
from src.api.auth import (
    login,
    register_user,
    get_current_user,
    get_current_user_token_data,
    LoginRequest,
    LoginResponse,
    create_access_token,
    get_password_hash,
)
from src.models.user import RegisterRequest
from src.config import GOOGLE_CLIENT_ID, JWT_ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["Authentication"])


class GoogleTokenRequest(BaseModel):
    id_token: str


@router.post("/auth/login", response_model=LoginResponse)
async def login_endpoint(request: LoginRequest):
    """Login endpoint to get JWT token."""
    logger.info(f"Login attempt for user: {request.username}")
    result = login(request.username, request.password)
    logger.info(f"Login successful for user: {request.username}")
    return result


@router.post("/auth/register")
async def register_endpoint(request: RegisterRequest):
    """Đăng ký tài khoản mới (role=user, status=active)."""
    result = register_user(request)
    logger.info(f"New user registered: {result['username']}")
    token_data = login(result["username"], request.password)
    return token_data


@router.post("/auth/logout")
async def logout_endpoint(current_user: str = Depends(get_current_user)):
    """Logout endpoint (token invalidation handled client-side)."""
    logger.info(f"Logout: {current_user}")
    return {"message": "Logged out successfully", "username": current_user}


@router.get("/auth/me")
async def get_current_user_info(token_data=Depends(get_current_user_token_data)):
    """Get current authenticated user info including role and profile."""
    users_col = get_users_collection()
    user_doc = users_col.find_one({"username": token_data.username})
    profile = {}
    if user_doc:
        profile = {
            "full_name": user_doc.get("full_name"),
            "email": user_doc.get("email"),
            "phone_number": user_doc.get("phone_number"),
            "telegram_username": user_doc.get("telegram_username"),
            "telegram_linked": bool(user_doc.get("telegram_session")),
        }
    return {
        "username": token_data.username,
        "role": token_data.role,
        "authenticated": True,
        **profile,
    }


@router.post("/auth/google")
async def google_oauth_login(body: GoogleTokenRequest):
    """Xác thực bằng Google Sign-In. Frontend gửi id_token, hệ thống trả về JWT nội bộ."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth chưa được cấu hình trên máy chủ.")

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Google token không hợp lệ: {exc}")

    google_email: str = id_info.get("email", "")
    google_name: str = id_info.get("name", "")
    google_sub: str = id_info.get("sub", "")

    if not google_email:
        raise HTTPException(status_code=400, detail="Không lấy được email từ tài khoản Google.")

    users_col = get_users_collection()
    user_doc = users_col.find_one({"email": google_email})

    if user_doc is None:
        username_base = google_email.split("@")[0].replace(".", "_")[:28]
        username = username_base
        suffix = 1
        while users_col.find_one({"username": username}):
            username = f"{username_base}_{suffix}"
            suffix += 1

        user_doc = {
            "username": username,
            "email": google_email,
            "full_name": google_name or username,
            "password_hash": get_password_hash(secrets.token_hex(32)),
            "role": "user",
            "status": "active",
            "google_sub": google_sub,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
        }
        users_col.insert_one(user_doc)
        logger.info(f"New Google user auto-registered: {username} ({google_email})")
    else:
        username = user_doc["username"]
        users_col.update_one({"_id": user_doc["_id"]}, {"$set": {"last_login": datetime.utcnow()}})

    role = user_doc.get("role", "user")
    access_token = create_access_token(
        {"sub": username, "role": role},
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"Google login successful: {username}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "username": username,
        "role": role,
    }
