"""Notification routes."""
from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException, Depends, Request

from src.db.mongo import get_db
from src.api.auth import get_current_user

router = APIRouter(tags=["Notifications"])


@router.get("/notifications")
async def get_notifications(
    request: Request,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: str = Depends(get_current_user),
):
    """Get notifications for current user."""
    db = get_db()
    coll = db["notifications"]

    query: dict = {"user": current_user}
    if unread_only:
        query["read"] = False

    cursor = coll.find(query).sort("created_at", -1).limit(limit)
    notifications = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)

    return {
        "notifications": notifications,
        "unread_count": coll.count_documents({"user": current_user, "read": False}),
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: str = Depends(get_current_user),
):
    """Mark a notification as read."""
    from bson import ObjectId

    db = get_db()
    coll = db["notifications"]

    result = coll.update_one(
        {"_id": ObjectId(notification_id), "user": current_user},
        {"$set": {"read": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}


@router.post("/notifications/mark-all-read")
async def mark_all_read(current_user: str = Depends(get_current_user)):
    """Mark all notifications as read."""
    db = get_db()
    coll = db["notifications"]

    result = coll.update_many({"user": current_user, "read": False}, {"$set": {"read": True}})
    return {"success": True, "updated": result.modified_count}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: str = Depends(get_current_user),
):
    """Delete a notification."""
    from bson import ObjectId

    db = get_db()
    coll = db["notifications"]

    result = coll.delete_one({"_id": ObjectId(notification_id), "user": current_user})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True}
