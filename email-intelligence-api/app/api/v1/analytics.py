"""Analytics API endpoints."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    OverviewStats, TimelineData, TopSendersResponse, EntityNetworkData
)

router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
def get_overview(db: Session = Depends(get_db)):
    """
    Get dashboard overview statistics.
    
    Returns:
    - Total email count
    - Entity counts (total and unique)
    - Alert counts (total and active)
    - Date range of emails
    - Entity breakdown by type
    - Alert breakdown by severity
    """
    service = AnalyticsService(db)
    return service.get_overview()


@router.get("/timeline", response_model=TimelineData)
def get_timeline(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_value: Optional[str] = Query(None, description="Filter by entity value"),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get entity mentions over time.
    
    Returns timeline data for visualization.
    
    - **granularity**: day, week, or month
    - **entity_type**: Optional filter by entity type
    - **entity_value**: Optional filter by specific entity value
    """
    service = AnalyticsService(db)
    timeline = service.get_timeline(
        entity_type=entity_type,
        entity_value=entity_value,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to
    )
    
    return TimelineData(timeline=timeline)


@router.get("/top-senders", response_model=TopSendersResponse)
def get_top_senders(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get most active email senders.
    
    Returns senders sorted by email count.
    """
    service = AnalyticsService(db)
    senders = service.get_top_senders(limit)
    
    return TopSendersResponse(senders=senders)


@router.get("/entity-network", response_model=EntityNetworkData)
def get_entity_network(
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated entity types to include"
    ),
    min_weight: int = Query(2, ge=1, description="Minimum edge weight"),
    limit: int = Query(100, ge=1, le=500, description="Maximum edges"),
    db: Session = Depends(get_db)
):
    """
    Get entity relationship network data.
    
    Returns nodes and edges for network visualization.
    Nodes are entities, edges represent co-occurrence in emails.
    """
    # Parse entity types
    types_list = None
    if entity_types:
        types_list = [t.strip() for t in entity_types.split(",")]
    
    service = AnalyticsService(db)
    network = service.get_entity_network(
        entity_types=types_list,
        min_weight=min_weight,
        limit=limit
    )
    
    return network


@router.get("/alerts-summary")
def get_alerts_summary(db: Session = Depends(get_db)):
    """
    Get alert statistics summary.
    
    Returns breakdown by status, severity, and rule.
    """
    service = AnalyticsService(db)
    return service.get_alerts_summary()

