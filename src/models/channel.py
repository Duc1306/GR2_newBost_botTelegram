"""Channel and Channel Summary models."""
from __future__ import annotations
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

ChannelStatus = Literal["pending", "active", "error"]


class Channel(BaseModel):
    """A Telegram channel registered in the system."""
    channel_link: str          # e.g. "t.me/javascript_news"
    username: str              # e.g. "javascript_news"
    display_name: Optional[str] = None
    status: ChannelStatus = "pending"
    added_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    post_count: int = 0


class ChannelSummary(BaseModel):
    """Daily AI-generated summary for a channel."""
    channel_username: str
    date: str                  # YYYY-MM-DD
    summary_text: str
    post_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SubscribeChannelRequest(BaseModel):
    """Request body for subscribing to a channel."""
    channel_link: str = Field(
        ...,
        description="Link kênh Telegram (VD: t.me/javascript_news hoặc @javascript_news)",
        min_length=2,
        max_length=200,
    )


class BulkSubscribeRequest(BaseModel):
    """Request body for bulk-subscribing to multiple channels at once."""
    channel_links: list[str] = Field(
        ...,
        description="Danh sách link kênh Telegram (tối đa 20 kênh mỗi lần)",
        min_length=1,
        max_length=20,
    )


class ChannelWithSummary(BaseModel):
    """Channel info with its latest summary — returned to the frontend."""
    channel_link: str
    username: str
    display_name: Optional[str] = None
    status: ChannelStatus
    added_at: datetime
    post_count: int
    latest_summary: Optional[str] = None
    summary_date: Optional[str] = None
    subscribed_at: datetime
    unread_count: int = 0
    summary_generating: bool = False
    error_message: Optional[str] = None   # set when status == "error"
