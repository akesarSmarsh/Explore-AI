"""Smarsh Alert Pydantic schemas - Enhanced alert system."""
from datetime import datetime
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field


# ============ Metric Configuration ============

class MetricConfig(BaseModel):
    """Configuration for what metric to monitor."""
    
    metric_type: Literal[
        "email_volume",      # Count of emails
        "unique_senders",    # Count of unique senders
        "entity_mentions",   # Count of entity mentions
        "keyword_matches"    # Count of keyword occurrences
    ] = Field("email_volume", description="Type of metric to monitor")
    
    # For entity_mentions
    entity_type: Optional[Literal["PERSON", "ORG", "GPE", "MONEY", "DATE", "PRODUCT", "EVENT", "ALL"]] = None
    entity_value: Optional[str] = Field(None, description="Specific entity to track")
    
    # For keyword_matches
    keywords: Optional[List[str]] = Field(None, description="Keywords to monitor")


# ============ Filter Configuration ============

class FilterConfig(BaseModel):
    """Dimension filters for scoping alerts."""
    
    sender_domains: Optional[List[str]] = Field(None, description="Filter by sender domains")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types present")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    file_formats: Optional[List[str]] = Field(None, description="Filter by source file format")


# ============ Time Window Configuration ============

class TimeWindowConfig(BaseModel):
    """Time window and aggregation settings."""
    
    # Evaluation window - how much data to analyze
    window_size: int = Field(1, ge=1, le=30, description="Window size value")
    window_unit: Literal["minutes", "hours", "days"] = Field("days", description="Window unit")
    
    # Check frequency - how often to evaluate
    check_frequency: int = Field(5, ge=1, description="How often to check (in minutes)")
    
    # Baseline period for anomaly detection (Smart Alerts)
    baseline_days: int = Field(7, ge=1, le=90, description="Days of history for baseline calculation")


# ============ Threshold Configuration ============

class ThresholdConfig(BaseModel):
    """Threshold settings for static alerts."""
    
    operator: Literal["greater_than", "less_than", "equals", "not_equals"] = "greater_than"
    value: float = Field(100, ge=0, description="Threshold value")


# ============ Anomaly Configuration ============

class AnomalyConfig(BaseModel):
    """Configuration for Smart/Anomaly alerts."""
    
    algorithm: Literal["zscore", "ewma", "percentage_change"] = Field(
        "zscore", 
        description="Anomaly detection algorithm"
    )
    
    # Z-score settings
    zscore_threshold: float = Field(
        2.5, 
        ge=1.0, 
        le=5.0, 
        description="Standard deviations for anomaly (2.5 = ~99% confidence)"
    )
    
    # EWMA settings
    ewma_span: int = Field(7, ge=2, description="EWMA span for smoothing")
    
    # Percentage change settings
    percentage_threshold: float = Field(50, ge=10, le=500, description="Percentage change threshold")
    
    # Minimum baseline count to avoid false positives
    min_baseline_count: int = Field(10, ge=1, description="Minimum data points for valid baseline")


# ============ Anti-Spam / Cooldown Configuration ============

class CooldownConfig(BaseModel):
    """Anti-spam and cooldown settings."""
    
    enabled: bool = Field(True, description="Enable cooldown controls")
    
    # Cooldown period after alert fires
    cooldown_minutes: int = Field(60, ge=5, le=1440, description="Minutes before re-alerting")
    
    # Max alerts per period
    max_alerts_per_day: int = Field(10, ge=1, le=100, description="Maximum alerts per day")
    
    # Alert longevity - require consecutive anomalies
    consecutive_anomalies: int = Field(1, ge=1, le=10, description="Consecutive anomalies required to trigger")


# ============ Notification Configuration ============

class NotificationConfig(BaseModel):
    """Notification channel settings."""
    
    # Email notifications
    email_enabled: bool = Field(True)
    email_recipients: List[str] = Field(default_factory=list)
    email_subject_template: str = Field(
        "🚨 Alert: {{alert_name}} - {{metric_type}} {{status}}",
        description="Email subject template"
    )
    
    # Dashboard indicator
    dashboard_enabled: bool = Field(True)
    
    # Webhook (Slack, Teams, etc.)
    webhook_enabled: bool = Field(False)
    webhook_url: Optional[str] = None
    
    # Include chart in notification
    include_chart: bool = Field(True, description="Include time-series chart in notification")


# ============ Main Alert Schema ============

class SmarshAlertCreate(BaseModel):
    """Schema for creating a Smarsh alert."""
    
    # Basic info
    name: str = Field(..., min_length=1, max_length=255, description="Alert name")
    description: Optional[str] = Field(None, description="Alert description")
    
    # Alert type
    alert_type: Literal["static", "smart"] = Field(
        "static",
        description="static = threshold-based, smart = anomaly-based"
    )
    
    # Metric configuration
    metric: MetricConfig = Field(default_factory=MetricConfig)
    
    # Filters
    filters: Optional[FilterConfig] = None
    
    # Time window
    time_window: TimeWindowConfig = Field(default_factory=TimeWindowConfig)
    
    # Threshold (for static alerts)
    threshold: Optional[ThresholdConfig] = None
    
    # Anomaly config (for smart alerts)
    anomaly: Optional[AnomalyConfig] = None
    
    # Anti-spam controls
    cooldown: CooldownConfig = Field(default_factory=CooldownConfig)
    
    # Notifications
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    
    # Settings
    severity: Literal["low", "medium", "high", "critical"] = Field("medium")
    enabled: bool = Field(True)


class SmarshAlertUpdate(BaseModel):
    """Schema for updating a Smarsh alert."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    alert_type: Optional[Literal["static", "smart"]] = None
    metric: Optional[MetricConfig] = None
    filters: Optional[FilterConfig] = None
    time_window: Optional[TimeWindowConfig] = None
    threshold: Optional[ThresholdConfig] = None
    anomaly: Optional[AnomalyConfig] = None
    cooldown: Optional[CooldownConfig] = None
    notifications: Optional[NotificationConfig] = None
    severity: Optional[Literal["low", "medium", "high", "critical"]] = None
    enabled: Optional[bool] = None


class SmarshAlertResponse(BaseModel):
    """Smarsh alert response schema."""
    
    id: str
    name: str
    description: Optional[str] = None
    alert_type: str
    
    # Configs stored as JSON
    metric: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None
    time_window: Dict[str, Any]
    threshold: Optional[Dict[str, Any]] = None
    anomaly: Optional[Dict[str, Any]] = None
    cooldown: Dict[str, Any]
    notifications: Dict[str, Any]
    
    severity: str
    enabled: bool
    
    # Tracking
    last_checked_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    alerts_today: int = 0
    consecutive_anomaly_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SmarshAlertListResponse(BaseModel):
    """List of Smarsh alerts."""
    total: int
    alerts: List[SmarshAlertResponse]


# ============ Evaluation Response ============

class TimeSeriesPoint(BaseModel):
    """Single point in time series."""
    timestamp: datetime
    value: float


class EvaluationResult(BaseModel):
    """Result of alert evaluation."""
    
    alert_id: str
    alert_name: str
    alert_type: str
    
    # Current state
    triggered: bool
    trigger_reason: Optional[str] = None
    
    # Metric values
    current_value: float = 0
    baseline_value: float = 0  # Mean for smart alerts, threshold for static
    
    # For smart alerts
    zscore: Optional[float] = None
    percentage_change: Optional[float] = None
    
    # Time series data (for charts)
    time_series: List[TimeSeriesPoint] = []
    
    # Cooldown status
    in_cooldown: bool = False
    cooldown_remaining_minutes: int = 0
    alerts_today: int = 0
    
    # Matched data
    top_contributors: List[Dict[str, Any]] = []


# ============ Alert History Response ============

class AlertHistoryItem(BaseModel):
    """Single alert history entry."""
    id: str
    alert_id: str
    alert_name: str
    severity: str
    triggered_at: datetime
    metric_value: float
    baseline_value: float
    zscore: Optional[float] = None
    percentage_change: Optional[float] = None
    trigger_reason: Optional[str] = None
    top_contributors: Optional[List[Dict[str, Any]]] = None


class AlertHistoryResponse(BaseModel):
    """Alert history response."""
    total: int
    history: List[AlertHistoryItem]


# ============ Statistics Response ============

class AlertStatsResponse(BaseModel):
    """Alert statistics."""
    total_alerts: int
    enabled_alerts: int
    triggered_last_24h: int
    by_severity: Dict[str, int]


# ============ Form Options ============

class FormOptionsResponse(BaseModel):
    """Available options for the alert creation form."""
    
    alert_types: List[dict] = [
        {"value": "static", "label": "Static Threshold", "description": "Trigger when metric exceeds/falls below a fixed value"},
        {"value": "smart", "label": "Smart Alert (Anomaly)", "description": "AI-powered detection of unusual patterns"},
    ]
    
    metric_types: List[dict] = [
        {"value": "email_volume", "label": "Email Volume", "description": "Count of emails in time window"},
        {"value": "unique_senders", "label": "Unique Senders", "description": "Count of unique email senders"},
        {"value": "entity_mentions", "label": "Entity Mentions", "description": "Count of entity mentions"},
        {"value": "keyword_matches", "label": "Keyword Matches", "description": "Count of keyword occurrences"},
    ]
    
    entity_types: List[dict] = [
        {"value": "ALL", "label": "All Entities"},
        {"value": "PERSON", "label": "Person"},
        {"value": "ORG", "label": "Organization"},
        {"value": "GPE", "label": "Location"},
        {"value": "MONEY", "label": "Money"},
        {"value": "DATE", "label": "Date"},
    ]
    
    operators: List[dict] = [
        {"value": "greater_than", "label": ">", "description": "Greater than"},
        {"value": "less_than", "label": "<", "description": "Less than"},
        {"value": "equals", "label": "=", "description": "Equals"},
    ]
    
    algorithms: List[dict] = [
        {"value": "zscore", "label": "Z-Score", "description": "Statistical anomaly detection"},
        {"value": "ewma", "label": "EWMA", "description": "Exponentially Weighted Moving Average"},
        {"value": "percentage_change", "label": "% Change", "description": "Percentage change from baseline"},
    ]
    
    window_units: List[dict] = [
        {"value": "minutes", "label": "Minutes"},
        {"value": "hours", "label": "Hours"},
        {"value": "days", "label": "Days"},
    ]
    
    severities: List[dict] = [
        {"value": "low", "label": "Low", "color": "#10b981"},
        {"value": "medium", "label": "Medium", "color": "#f59e0b"},
        {"value": "high", "label": "High", "color": "#f97316"},
        {"value": "critical", "label": "Critical", "color": "#ef4444"},
    ]
