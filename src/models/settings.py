"""
User settings model.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class UserSettings(BaseModel):
    """User settings model."""
    
    username: str
    theme: str = "light"  # 'light' or 'dark'
    notifications_enabled: bool = True
    email_notifications: bool = False
    telegram_enabled: bool = True
    twitter_enabled: bool = True
    fetch_frequency_hours: int = 6  # How often to fetch new posts
    ml_auto_classify: bool = True
    ml_confidence_threshold: float = 0.5
    default_date_range_days: int = 7
    posts_per_page: int = 20
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "theme": "light",
                "notifications_enabled": True,
                "fetch_frequency_hours": 6,
                "ml_confidence_threshold": 0.5
            }
        }

class UpdatePasswordRequest(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str
    
class UpdateSettingsRequest(BaseModel):
    """Request model for settings update."""
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    twitter_enabled: Optional[bool] = None
    fetch_frequency_hours: Optional[int] = None
    ml_auto_classify: Optional[bool] = None
    ml_confidence_threshold: Optional[float] = None
    default_date_range_days: Optional[int] = None
    posts_per_page: Optional[int] = None
