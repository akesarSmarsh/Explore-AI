"""Search Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Filters for search queries."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    entity_types: Optional[List[str]] = None
    sender: Optional[str] = None


class SemanticSearchRequest(BaseModel):
    """Semantic search request."""
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    filters: Optional[SearchFilters] = None


class SearchResult(BaseModel):
    """Single search result."""
    email_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    date: Optional[datetime] = None
    relevance_score: float
    snippet: Optional[str] = None
    matched_entities: List[str] = []


class SemanticSearchResponse(BaseModel):
    """Semantic search response."""
    results: List[SearchResult]
    query_embedding_id: Optional[str] = None


class SimilarEmailRequest(BaseModel):
    """Find similar emails request."""
    email_id: str
    limit: int = Field(default=10, ge=1, le=50)


class KeywordSearchRequest(BaseModel):
    """Keyword search request."""
    query: str = Field(min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    filters: Optional[SearchFilters] = None

