"""Search API endpoints."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.search_service import SearchService
from app.schemas.search import (
    SemanticSearchRequest, SemanticSearchResponse,
    SimilarEmailRequest, KeywordSearchRequest, SearchFilters
)

router = APIRouter()


@router.post("/semantic", response_model=SemanticSearchResponse)
def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search on emails using natural language (POST version).
    
    Examples:
    - "emails about financial irregularities"
    - "discussions about quarterly reports"
    - "messages mentioning layoffs or restructuring"
    
    The search uses AI embeddings to find semantically similar content,
    not just keyword matches.
    
    **Request body:**
    ```json
    {
        "query": "your search query",
        "limit": 20,
        "filters": {
            "date_from": "2024-01-01T00:00:00",
            "date_to": "2024-12-31T23:59:59",
            "sender": "john@example.com"
        }
    }
    ```
    """
    service = SearchService(db)
    results = service.semantic_search(request)
    
    return SemanticSearchResponse(results=results)


@router.get("/semantic", response_model=SemanticSearchResponse)
def semantic_search_get(
    query: str = Query(..., min_length=3, max_length=500, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    date_from: Optional[datetime] = Query(None, description="Filter emails from this date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter emails until this date (ISO format)"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    db: Session = Depends(get_db)
):
    """
    Perform semantic search on emails using natural language (GET version with query params).
    
    **Time Range Filter Examples:**
    - Last 24 hours: `date_from=2024-12-03T00:00:00`
    - Last 7 days: `date_from=2024-11-27T00:00:00`
    - Specific range: `date_from=2024-01-01&date_to=2024-06-30`
    
    **Example Requests:**
    - `/api/v1/search/semantic?query=financial irregularities&limit=20`
    - `/api/v1/search/semantic?query=quarterly reports&date_from=2024-01-01T00:00:00`
    - `/api/v1/search/semantic?query=layoffs&date_from=2024-06-01&date_to=2024-12-01`
    
    The search uses AI embeddings to find semantically similar content,
    not just keyword matches.
    """
    # Build filters if any provided
    filters = None
    if date_from or date_to or sender:
        filters = SearchFilters(
            date_from=date_from,
            date_to=date_to,
            sender=sender
        )
    
    # Create request object
    request = SemanticSearchRequest(
        query=query,
        limit=limit,
        filters=filters
    )
    
    service = SearchService(db)
    results = service.semantic_search(request)
    
    return SemanticSearchResponse(results=results)


@router.post("/similar", response_model=SemanticSearchResponse)
def find_similar_emails(
    request: SimilarEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Find emails similar to a given email.
    
    Uses the email's embedding to find other emails with similar content.
    """
    service = SearchService(db)
    results = service.find_similar(request)
    
    return SemanticSearchResponse(results=results)


@router.get("/keyword")
def keyword_search(
    query: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sender: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Perform keyword search on emails.
    
    Searches in email subject and body using exact text matching.
    """
    filters = SearchFilters(
        date_from=date_from,
        date_to=date_to,
        sender=sender
    )
    
    request = KeywordSearchRequest(
        query=query,
        page=page,
        limit=limit,
        filters=filters
    )
    
    service = SearchService(db)
    results, total = service.keyword_search(request)
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": results
    }

