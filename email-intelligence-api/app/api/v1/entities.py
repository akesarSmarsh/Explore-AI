"""Entity API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.entity_service import EntityService
from app.schemas.entity import (
    EntityListResponse, EntityTypesResponse,
    EntityCoOccurrenceResponse, EntityAggregated
)

router = APIRouter()


@router.get("", response_model=EntityListResponse)
def list_entities(
    type: Optional[str] = Query(None, description="Filter by entity type"),
    min_count: int = Query(1, ge=1, description="Minimum occurrence count"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    sort_by: str = Query("count", description="Sort by count or text"),
    db: Session = Depends(get_db)
):
    """
    List all unique entities with aggregated counts.
    
    Returns entities sorted by occurrence count by default.
    """
    service = EntityService(db)
    entities = service.list_entities(
        entity_type=type,
        min_count=min_count,
        limit=limit,
        sort_by=sort_by
    )
    
    return EntityListResponse(
        total=len(entities),
        entities=[EntityAggregated(**e) for e in entities]
    )


@router.get("/types", response_model=EntityTypesResponse)
def get_entity_types(db: Session = Depends(get_db)):
    """
    Get entity type statistics.
    
    Returns count and unique count for each entity type.
    """
    service = EntityService(db)
    types = service.get_entity_types()
    
    return EntityTypesResponse(types=types)


@router.get("/co-occurrences", response_model=EntityCoOccurrenceResponse)
def get_co_occurrences(
    entity_type_1: Optional[str] = Query(None, description="First entity type filter"),
    entity_type_2: Optional[str] = Query(None, description="Second entity type filter"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    Get entity co-occurrence data.
    
    Shows which entities appear together in the same emails.
    Useful for finding relationships between people, organizations, etc.
    """
    service = EntityService(db)
    co_occurrences = service.get_co_occurrences(
        entity_type_1=entity_type_1,
        entity_type_2=entity_type_2,
        limit=limit
    )
    
    return EntityCoOccurrenceResponse(co_occurrences=co_occurrences)


@router.get("/{entity_type}", response_model=EntityListResponse)
def get_entities_by_type(
    entity_type: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get entities of a specific type.
    
    Valid types: PERSON, ORG, GPE, LOC, DATE, TIME, MONEY, PERCENT, EMAIL, PHONE
    """
    service = EntityService(db)
    entities = service.get_entities_by_type(entity_type, limit)
    
    return EntityListResponse(
        total=len(entities),
        entities=[EntityAggregated(**e) for e in entities]
    )

