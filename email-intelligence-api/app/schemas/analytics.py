"""Analytics Pydantic schemas."""
from datetime import date, datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """Date range."""
    from_date: Optional[date] = Field(None, alias="from")
    to_date: Optional[date] = Field(None, alias="to")
    
    class Config:
        populate_by_name = True


class OverviewStats(BaseModel):
    """Dashboard overview statistics."""
    total_emails: int
    total_entities: int
    unique_entities: int
    total_alerts: int
    active_alerts: int
    date_range: DateRange
    entity_breakdown: Dict[str, int]
    alert_breakdown: Dict[str, int]


class TimelineDataPoint(BaseModel):
    """Single data point in timeline."""
    date: str
    count: int


class TimelineData(BaseModel):
    """Timeline data response."""
    timeline: List[TimelineDataPoint]


class TopSender(BaseModel):
    """Top sender data."""
    sender: str
    email_count: int
    entity_count: int


class TopSendersResponse(BaseModel):
    """Top senders response."""
    senders: List[TopSender]


class NetworkNode(BaseModel):
    """Node in entity network."""
    id: str
    type: str
    count: int


class NetworkEdge(BaseModel):
    """Edge in entity network."""
    source: str
    target: str
    weight: int


class EntityNetworkData(BaseModel):
    """Entity network graph data."""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]

