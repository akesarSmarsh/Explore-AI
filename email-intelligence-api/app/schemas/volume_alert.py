"""Volume-based Alert Pydantic schemas for POC - Form-based alerts."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr


# ============ Volume Alert Schemas ============

class VolumeAlertCreate(BaseModel):
    """Schema for creating a volume-based alert via form."""
    
    # Alert identification
    name: str = Field(..., min_length=1, max_length=255, description="Name of the alert")
    description: Optional[str] = Field(None, description="Description of the alert")
    
    # Alert type
    alert_type: Literal["volume_spike", "volume_threshold", "volume_drop"] = Field(
        "volume_spike",
        description="Type of volume alert"
    )
    
    # File format filter (optional - to filter by source file format)
    file_format: Optional[Literal["csv", "eml", "pst", "all"]] = Field(
        "all",
        description="File format to monitor"
    )
    
    # Entity configuration
    entity_type: Literal["PERSON", "ORG", "GPE", "MONEY", "DATE", "PRODUCT", "EVENT", "ALL"] = Field(
        "ALL",
        description="Entity type to monitor"
    )
    entity_value: Optional[str] = Field(
        None,
        description="Specific entity value to monitor (leave empty for all entities of type)"
    )
    
    # Threshold parameter
    threshold_value: int = Field(
        50, 
        ge=1, 
        le=1000,
        description="Threshold value (e.g., 50 means 50% increase for volume_spike)"
    )
    threshold_type: Literal["percentage", "absolute"] = Field(
        "percentage",
        description="Threshold type - percentage increase or absolute count"
    )
    
    # Duration / monitoring window
    duration: Literal["1_day", "2_days", "3_days", "7_days"] = Field(
        "1_day",
        description="Monitoring window duration"
    )
    
    # Notification settings
    subscriber_emails: List[str] = Field(
        default_factory=list,
        description="Email addresses to notify when alert triggers"
    )
    
    # Alert settings
    severity: Literal["low", "medium", "high", "critical"] = Field("medium")
    enabled: bool = Field(True)


class VolumeAlertUpdate(BaseModel):
    """Schema for updating a volume-based alert."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    alert_type: Optional[Literal["volume_spike", "volume_threshold", "volume_drop"]] = None
    file_format: Optional[Literal["csv", "eml", "pst", "all"]] = None
    entity_type: Optional[Literal["PERSON", "ORG", "GPE", "MONEY", "DATE", "PRODUCT", "EVENT", "ALL"]] = None
    entity_value: Optional[str] = None
    threshold_value: Optional[int] = Field(None, ge=1, le=1000)
    threshold_type: Optional[Literal["percentage", "absolute"]] = None
    duration: Optional[Literal["1_day", "2_days", "3_days", "7_days"]] = None
    subscriber_emails: Optional[List[str]] = None
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    enabled: Optional[bool] = None


class VolumeAlertResponse(BaseModel):
    """Volume alert response schema."""
    
    id: str
    name: str
    description: Optional[str] = None
    alert_type: str
    file_format: str
    entity_type: str
    entity_value: Optional[str] = None
    threshold_value: int
    threshold_type: str
    duration: str
    subscriber_emails: List[str] = []
    severity: str
    enabled: bool
    
    # Tracking
    last_checked_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VolumeAlertListResponse(BaseModel):
    """List of volume alerts."""
    total: int
    alerts: List[VolumeAlertResponse]


# ============ Alert Trigger Response ============

class VolumeAlertTriggerResponse(BaseModel):
    """Response when a volume alert is triggered."""
    
    alert_id: str
    alert_name: str
    triggered: bool
    trigger_reason: Optional[str] = None
    current_volume: int = 0
    baseline_volume: int = 0
    change_percentage: float = 0.0
    matched_entities: List[dict] = []


# ============ Form Options Response ============

class AlertFormOptionsResponse(BaseModel):
    """Available options for the alert creation form."""
    
    alert_types: List[dict] = [
        {"value": "volume_spike", "label": "Volume Spike", "description": "Trigger when entity mentions exceed baseline"},
        {"value": "volume_threshold", "label": "Volume Threshold", "description": "Trigger when mentions exceed a fixed count"},
        {"value": "volume_drop", "label": "Volume Drop", "description": "Trigger when mentions drop below baseline"},
    ]
    
    file_formats: List[dict] = [
        {"value": "all", "label": "All Formats"},
        {"value": "csv", "label": "CSV Files"},
        {"value": "eml", "label": "Email Files (.eml)"},
        {"value": "pst", "label": "Outlook Files (.pst)"},
    ]
    
    entity_types: List[dict] = [
        {"value": "ALL", "label": "All Entities"},
        {"value": "PERSON", "label": "Person"},
        {"value": "ORG", "label": "Organization"},
        {"value": "GPE", "label": "Location"},
        {"value": "MONEY", "label": "Money"},
        {"value": "DATE", "label": "Date"},
        {"value": "PRODUCT", "label": "Product"},
        {"value": "EVENT", "label": "Event"},
    ]
    
    durations: List[dict] = [
        {"value": "1_day", "label": "1 Day"},
        {"value": "2_days", "label": "2 Days"},
        {"value": "3_days", "label": "3 Days"},
        {"value": "7_days", "label": "7 Days"},
    ]
    
    threshold_types: List[dict] = [
        {"value": "percentage", "label": "Percentage"},
        {"value": "absolute", "label": "Absolute Count"},
    ]
    
    severities: List[dict] = [
        {"value": "low", "label": "Low"},
        {"value": "medium", "label": "Medium"},
        {"value": "high", "label": "High"},
        {"value": "critical", "label": "Critical"},
    ]

