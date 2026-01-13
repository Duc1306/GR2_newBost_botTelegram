"""
Notification model for user notifications.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Notification(BaseModel):
    """Notification model for alerts and updates."""
    
    id: Optional[str] = Field(None, alias="_id")
    user: str  # Username
    type: str  # 'info', 'success', 'warning', 'error'
    title: str
    message: str
    link: Optional[str] = None  # Optional link to related resource
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    user: str
    type: str
    title: str
    message: str
    link: Optional[str] = None
