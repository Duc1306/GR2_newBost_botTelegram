"""Post model using Pydantic v2.
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field
import hashlib

class MediaItem(BaseModel):
    type: str = Field(description="photo|video|gif|other")
    url: str

class Post(BaseModel):
    id: str
    source: str
    source_id: str
    author: Optional[str] = None
    text: str
    links: List[str] = []
    media: List[MediaItem] = []
    lang: Optional[str] = None
    created_at: datetime
    fetched_at: datetime
    dedupe_key: str
    topics: List[str] = []
    score: float = 0.0

    @staticmethod
    def make_id(source: str, source_id: str) -> str:
        return f"{source}:{source_id}"  # simple composite id

    @staticmethod
    def make_dedupe_key(text: str, links: List[str]) -> str:
        base = text + "|" + "|".join(sorted(links))
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def from_raw(cls, *, source: str, source_id: str, author: Optional[str], text: str, links: List[str], media: List[MediaItem], created_at: datetime) -> "Post":
        # timezone-aware datetimes (UTC) để tránh cảnh báo deprecated
        fetched_at = datetime.now(UTC)
        dedupe_key = cls.make_dedupe_key(text, links)
        return cls(
            id=cls.make_id(source, source_id),
            source=source,
            source_id=source_id,
            author=author,
            text=text,
            links=links,
            media=media,
            lang=None,
            created_at=created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC),
            fetched_at=fetched_at,
            dedupe_key=dedupe_key,
            topics=[],
            score=0.0,
        )
