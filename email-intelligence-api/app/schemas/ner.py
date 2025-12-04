"""NER visualization Pydantic schemas."""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WordCloudEntity(BaseModel):
    """Single entity for word cloud."""
    text: str
    type: str
    count: int
    weight: float  # Normalized weight (0-1) for visualization


class WordCloudResponse(BaseModel):
    """Word cloud response."""
    entities: List[WordCloudEntity]
    total_entities: int
    max_count: int
    filters_applied: Dict[str, Any]


class EntityTypeBreakdown(BaseModel):
    """Entity type statistics."""
    type: str
    count: int
    unique_count: int
    percentage: float


class BreakdownResponse(BaseModel):
    """Entity breakdown response."""
    types: List[EntityTypeBreakdown]
    total_entities: int
    total_unique: int


class TrendingDataPoint(BaseModel):
    """Single data point for trending."""
    date: str
    count: int
    entities: List[Dict[str, Any]] = []  # Top entities for that period


class TrendingResponse(BaseModel):
    """Trending entities response."""
    timeline: List[TrendingDataPoint]
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    granularity: str


class TopEntity(BaseModel):
    """Top entity with details."""
    text: str
    type: str
    count: int
    email_count: int
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None
    trend: Optional[str] = None  # "up", "down", "stable"


class TopEntitiesResponse(BaseModel):
    """Top entities response."""
    entities: List[TopEntity]
    total: int
    filters_applied: Dict[str, Any]


class NERFilters(BaseModel):
    """Common filters for NER endpoints."""
    entity_types: Optional[str] = Field(None, description="Comma-separated entity types")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sender: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=500)
    min_count: int = Field(default=1, ge=1)


class MatchedEntityInEmail(BaseModel):
    """Entity matched in an email."""
    text: str
    type: str
    sentence: Optional[str] = None


class EmailByEntityResult(BaseModel):
    """Single email result for entity search."""
    id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[str] = None
    preview: Optional[str] = None
    matched_entities: List[MatchedEntityInEmail] = []
    total_matched: int = 0


class EmailsByEntityResponse(BaseModel):
    """Response for emails by entity search."""
    entity_text: str
    entity_type: Optional[str] = None
    total: int
    page: int
    limit: int
    total_pages: int
    emails: List[EmailByEntityResult]








