"""Entity Pydantic schemas."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class EntityBase(BaseModel):
    """Base entity schema."""
    text: str
    type: str
    start_pos: int
    end_pos: int
    sentence: Optional[str] = None


class EntityResponse(BaseModel):
    """Entity response schema."""
    id: str
    email_id: str
    text: str
    type: str
    start_pos: int
    end_pos: int
    sentence: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EntityAggregated(BaseModel):
    """Aggregated entity with counts."""
    text: str
    type: str
    count: int
    email_count: int
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None


class EntityListResponse(BaseModel):
    """List of aggregated entities."""
    total: int
    entities: List[EntityAggregated]


class EntityTypeStats(BaseModel):
    """Entity type statistics."""
    type: str
    count: int
    unique: int


class EntityTypesResponse(BaseModel):
    """Response with entity type statistics."""
    types: List[EntityTypeStats]


class EntityCoOccurrence(BaseModel):
    """Entity co-occurrence data."""
    entity1: dict  # {"text": str, "type": str}
    entity2: dict  # {"text": str, "type": str}
    count: int
    emails: List[str] = []


class EntityCoOccurrenceResponse(BaseModel):
    """Response with entity co-occurrences."""
    co_occurrences: List[EntityCoOccurrence]


class EntityFilters(BaseModel):
    """Entity query filters."""
    type: Optional[str] = None
    min_count: int = Field(default=1, ge=1)
    limit: int = Field(default=100, ge=1, le=1000)
    sort_by: str = Field(default="count")

