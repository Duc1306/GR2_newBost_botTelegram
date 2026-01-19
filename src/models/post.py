"""Post model using Pydantic v2.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from datetime import datetime, UTC
from pydantic import BaseModel, Field
import hashlib

class MediaItem(BaseModel):
    type: str = Field(description="photo|video|gif|document|other")
    url: str
    thumbnail: Optional[str] = None

class TopicPrediction(BaseModel):
    """ML/Rule-based topic prediction with metadata."""
    model_config = {"protected_namespaces": ()}  # Allow model_* field names
    
    topic: str
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str
    predicted_at: datetime
    method: Literal["ml", "rule-based", "manual"] = "ml"

class FullArticle(BaseModel):
    """Scraped full article content."""
    title: str
    content: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    scraped_at: datetime

class Post(BaseModel):
    id: str
    
    # Platform & Source
    platform: Literal["telegram", "twitter"] = "telegram"
    source: str
    source_id: str
    author: Optional[str] = None
    
    # Content
    text: str
    text_cleaned: Optional[str] = None  # Preprocessed text for ML
    links: List[str] = []
    media: List[MediaItem] = []
    lang: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    fetched_at: datetime
    
    # Deduplication
    dedupe_key: str
    
    # Topics (Legacy - for backward compatibility)
    topics: List[str] = []
    
    # Ground Truth from News Source (BEST quality)
    source_category: Optional[str] = Field(default=None, description="Original category from news website (e.g., 'kinh-te', 'suc-khoe')")
    source_topic: Optional[str] = Field(default=None, description="Topic extracted from news URL/page (ground truth)")
    
    # Topic Predictions (NEW - with confidence + version tracking)
    topic_predictions: List[TopicPrediction] = []
    
    # Manual Labels (Ground Truth - Fallback)
    manual_labels: List[str] = Field(default=[], description="Manually verified topic labels (ground truth)")
    labels_verified: bool = Field(default=False, description="Whether labels have been manually verified")
    verified_by: Optional[str] = Field(default=None, description="Username who verified the labels")
    verified_at: Optional[datetime] = Field(default=None, description="When labels were verified")
    
    # Scoring
    score: float = 0.0
    
    # Full Article (if scraped)
    full_article: Optional[FullArticle] = None

    @staticmethod
    def make_id(source: str, source_id: str, platform: str = "telegram") -> str:
        return f"{platform}:{source}:{source_id}"

    @staticmethod
    def make_dedupe_key(text: str, links: List[str]) -> str:
        base = text + "|" + "|".join(sorted(links))
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def from_raw(
        cls, 
        *, 
        platform: str = "telegram",
        source: str, 
        source_id: str, 
        author: Optional[str], 
        text: str, 
        links: List[str], 
        media: List[MediaItem], 
        created_at: datetime
    ) -> "Post":
        """Create Post from raw data."""
        # timezone-aware datetimes (UTC)
        fetched_at = datetime.now(UTC)
        dedupe_key = cls.make_dedupe_key(text, links)
        
        return cls(
            id=cls.make_id(source, source_id, platform),
            platform=platform,
            source=source,
            source_id=source_id,
            author=author,
            text=text,
            text_cleaned=None,  # Will be filled by cleaning pipeline
            links=links,
            media=media,
            lang=None,
            created_at=created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=UTC),
            fetched_at=fetched_at,
            dedupe_key=dedupe_key,
            topics=[],
            topic_predictions=[],
            score=0.0,
            full_article=None
        )
    
    def add_topic_prediction(
        self,
        topic: str,
        confidence: float,
        model_version: str,
        method: Literal["ml", "rule-based", "manual"] = "ml"
    ) -> None:
        """Add a new topic prediction (append to history)."""
        prediction = TopicPrediction(
            topic=topic,
            confidence=confidence,
            model_version=model_version,
            predicted_at=datetime.now(UTC),
            method=method
        )
        self.topic_predictions.append(prediction)
    
    def get_primary_topic(self, min_confidence: float = 0.0, prefer_manual: bool = True) -> Optional[str]:
        """Get highest confidence topic above threshold.
        
        Args:
            min_confidence: Minimum confidence threshold for predictions
            prefer_manual: If True, return manual label if available
            
        Returns:
            Primary topic or None
        """
        # Prefer manual labels if verified
        if prefer_manual and self.labels_verified and self.manual_labels:
            return self.manual_labels[0]
        
        valid_predictions = [
            p for p in self.topic_predictions 
            if p.confidence >= min_confidence
        ]
        
        if not valid_predictions:
            return None
        
        # Sort by confidence desc, then by prediction time desc
        sorted_preds = sorted(
            valid_predictions,
            key=lambda p: (p.confidence, p.predicted_at),
            reverse=True
        )
        
        return sorted_preds[0].topic
    
    def set_manual_labels(self, labels: List[str], verified_by: str) -> None:
        """Set manual labels and mark as verified (ground truth).
        
        Args:
            labels: List of manually assigned topic labels
            verified_by: Username who verified the labels
        """
        self.manual_labels = labels
        self.labels_verified = True
        self.verified_by = verified_by
        self.verified_at = datetime.now(UTC)
