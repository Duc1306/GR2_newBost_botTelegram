"""Settings routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from src.db.mongo import get_db
from src.api.auth import get_current_user

router = APIRouter(tags=["Settings"])


@router.get("/settings")
async def get_settings(current_user: str = Depends(get_current_user)):
    """Get user settings."""
    from src.models.settings import UserSettings

    db = get_db()
    coll = db["user_settings"]

    settings = coll.find_one({"username": current_user})
    if not settings:
        default_settings = UserSettings(username=current_user).dict()
        coll.insert_one(default_settings)
        return default_settings

    settings.pop("_id", None)
    return settings


@router.put("/settings")
async def update_settings(
    settings: dict,
    current_user: str = Depends(get_current_user),
):
    """Update user settings."""
    db = get_db()
    coll = db["user_settings"]

    updates = {k: v for k, v in settings.items() if v is not None and k != "username"}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    coll.update_one({"username": current_user}, {"$set": updates}, upsert=True)
    logger.info(f"Settings updated for {current_user}: {list(updates.keys())}")
    return {"success": True, "updated_fields": list(updates.keys())}


@router.post("/settings/change-password")
async def change_password(
    request: dict,
    current_user: str = Depends(get_current_user),
):
    """Change user password."""
    from src.api.auth import authenticate_user, get_password_hash

    current_password = request.get("current_password")
    new_password = request.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current and new password are required")

    if not authenticate_user(current_user, current_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải từ 6 ký tự trở lên.")

    from src.db.mongo import get_users_collection
    users_col = get_users_collection()
    result = users_col.update_one(
        {"username": current_user},
        {"$set": {"password_hash": get_password_hash(new_password)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Tài khoản admin env không thể đổi mật khẩu qua đây.")

    logger.info(f"Password changed for {current_user}")
    return {"message": "Đổi mật khẩu thành công."}
