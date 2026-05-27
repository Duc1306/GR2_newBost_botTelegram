"""Authentication routes: login, register, logout, me."""
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
from src.config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(tags=["Authentication"])


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
            "has_password": bool(user_doc.get("password_hash")),
        }
    return {
        "username": token_data.username,
        "role": token_data.role,
        "authenticated": True,
        **profile,
    }


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None


@router.put("/auth/profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: str = Depends(get_current_user),
):
    """Update current user's profile (full_name, email)."""
    users_col = get_users_collection()
    updates: dict = {}
    if request.full_name is not None:
        name = request.full_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Họ tên không được để trống.")
        updates["full_name"] = name
    if request.email is not None:
        email = request.email.strip()
        # Basic email format check
        if email and "@" not in email:
            raise HTTPException(status_code=400, detail="Email không hợp lệ.")
        updates["email"] = email

    if not updates:
        raise HTTPException(status_code=400, detail="Không có trường nào cần cập nhật.")

    result = users_col.update_one({"username": current_user}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    logger.info(f"Profile updated for {current_user}: {list(updates.keys())}")
    return {"success": True, "updated_fields": list(updates.keys())}

