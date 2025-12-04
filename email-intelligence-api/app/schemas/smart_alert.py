"""Smart Alert Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


# ============ Time Window Configuration ============

class TimeWindow(BaseModel):
    """Time window configuration."""
    duration: int = Field(ge=1, description="Duration value")
    unit: Literal["hours", "days", "weeks"] = "hours"


# ============ Threshold Configuration ============

class ThresholdConfig(BaseModel):
    """Threshold configuration for anomaly detection."""
    type: Literal["percentage", "multiplier", "std_deviation", "absolute"]
    value: float = Field(gt=0)


# ============ Anomaly Configuration ============

class AnomalyConfig(BaseModel):
    """Anomaly detection configuration."""
    entity_type: Optional[str] = Field(None, description="Entity type to monitor (PERSON, ORG, etc.)")
    entity_value: Optional[str] = Field(None, description="Specific entity to monitor")
    monitoring_window: TimeWindow = Field(default_factory=lambda: TimeWindow(duration=24, unit="hours"))
    baseline_period: TimeWindow = Field(default_factory=lambda: TimeWindow(duration=7, unit="days"))
    threshold: ThresholdConfig
    min_baseline_count: int = Field(default=5, ge=1, description="Minimum baseline count to avoid false positives")


# ============ Standard Alert Conditions ============

class EntityThresholdCondition(BaseModel):
    """Condition for entity value threshold."""
    entity_type: str
    operator: Literal["greater_than", "less_than", "equals"]
    value: float


class EntityMentionCondition(BaseModel):
    """Condition for specific entity mention."""
    entities: List[str]
    match_type: Literal["exact", "contains"] = "exact"


class KeywordMatchCondition(BaseModel):
    """Condition for keyword matching."""
    keywords: List[str]
    match_all: bool = False  # If true, all keywords must match


class CoOccurrenceCondition(BaseModel):
    """Condition for entity co-occurrence."""
    entity_type_1: str
    entity_type_2: str
    same_sentence: bool = True


class PatternMatchCondition(BaseModel):
    """Condition for regex pattern matching."""
    pattern: str
    field: Literal["subject", "body", "sender"] = "body"


# ============ Schedule Configuration ============

class ScheduleConfig(BaseModel):
    """Alert schedule configuration."""
    type: Literal["realtime", "scheduled"] = "realtime"
    frequency: Optional[Literal["hourly", "daily", "weekly"]] = None
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Time in HH:MM format")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0=Monday, 6=Sunday")


# ============ Notification Configuration ============

class EmailNotificationConfig(BaseModel):
    """Email notification settings."""
    enabled: bool = True
    recipients: List[str] = []
    subject_template: Optional[str] = "Alert: {{alert_name}} triggered"
    body_template: Optional[str] = None


class NotificationConfig(BaseModel):
    """Overall notification configuration."""
    email: Optional[EmailNotificationConfig] = None


# ============ Main Smart Alert Schemas ============

class SmartAlertBase(BaseModel):
    """Base smart alert schema."""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    alert_type: Literal[
        "entity_threshold", "entity_mention", "keyword_match",
        "co_occurrence", "pattern_match",
        "volume_spike", "sudden_appearance", "frequency_change"
    ]
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    enabled: bool = True


class SmartAlertCreate(SmartAlertBase):
    """Schema for creating a smart alert."""
    # Standard alert conditions (for non-anomaly types)
    conditions: Optional[Dict[str, Any]] = None
    
    # Anomaly detection config (for volume_spike, sudden_appearance, frequency_change)
    anomaly_config: Optional[AnomalyConfig] = None
    
    # Optional filters
    filters: Optional[Dict[str, Any]] = None
    
    # Schedule configuration
    schedule: Optional[ScheduleConfig] = None
    
    # Notification configuration
    notifications: Optional[NotificationConfig] = None


class SmartAlertUpdate(BaseModel):
    """Schema for updating a smart alert."""
    name: Optional[str] = None
    description: Optional[str] = None
    alert_type: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    anomaly_config: Optional[AnomalyConfig] = None
    filters: Optional[Dict[str, Any]] = None
    schedule: Optional[ScheduleConfig] = None
    notifications: Optional[NotificationConfig] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


class SmartAlertResponse(SmartAlertBase):
    """Smart alert response schema."""
    id: str
    conditions: Optional[Dict[str, Any]] = None
    anomaly_config: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    last_checked_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SmartAlertListResponse(BaseModel):
    """List of smart alerts."""
    total: int
    alerts: List[SmartAlertResponse]


# ============ Alert History Schemas ============

class AlertHistoryResponse(BaseModel):
    """Alert history response."""
    id: str
    smart_alert_id: str
    smart_alert_name: Optional[str] = None
    email_id: Optional[str] = None
    email_subject: Optional[str] = None
    triggered_at: datetime
    matched_data: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    notification_sent: bool
    notification_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertHistoryListResponse(BaseModel):
    """List of alert history entries."""
    total: int
    history: List[AlertHistoryResponse]


# ============ Test Alert Schema ============

class TestAlertRequest(BaseModel):
    """Request to test an alert against sample data."""
    sample_size: int = Field(default=100, ge=1, le=1000)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class TestAlertMatch(BaseModel):
    """Single test match result."""
    email_id: str
    email_subject: Optional[str] = None
    matched_data: Dict[str, Any]


class TestAlertResponse(BaseModel):
    """Test alert response."""
    alert_id: str
    alert_name: str
    sample_size: int
    match_count: int
    matches: List[TestAlertMatch]
    would_trigger: bool










