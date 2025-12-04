"""Email Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EmailBase(BaseModel):
    """Base email schema."""
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[List[str]] = []
    cc: Optional[List[str]] = []
    date: Optional[datetime] = None
    body: Optional[str] = None


class EmailCreate(EmailBase):
    """Schema for creating an email."""
    message_id: Optional[str] = None
    raw_file_path: Optional[str] = None


class EntityInEmail(BaseModel):
    """Entity embedded in email response."""
    text: str
    type: str
    start: int
    end: int
    sentence: Optional[str] = None


class AlertInEmail(BaseModel):
    """Alert embedded in email response."""
    id: str
    rule_name: str
    severity: str
    matched_entity: Optional[str] = None


class EmailResponse(BaseModel):
    """Email response schema for list view."""
    id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: List[str] = []
    date: Optional[datetime] = None
    preview: Optional[str] = None
    entity_counts: Dict[str, int] = {}
    alert_count: int = 0
    
    class Config:
        from_attributes = True


class EmailDetailResponse(BaseModel):
    """Detailed email response with entities and alerts."""
    id: str
    message_id: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: List[str] = []
    cc: List[str] = []
    date: Optional[datetime] = None
    body: Optional[str] = None
    body_html: Optional[str] = None  # Body with highlighted entities
    entities: List[EntityInEmail] = []
    alerts: List[AlertInEmail] = []
    similar_emails: List[str] = []
    
    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Paginated list of emails."""
    total: int
    page: int
    limit: int
    emails: List[EmailResponse]


class EmailFilters(BaseModel):
    """Email query filters."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="date")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sender: Optional[str] = None
    entity_type: Optional[str] = None
    entity_value: Optional[str] = None
    has_alert: Optional[bool] = None

