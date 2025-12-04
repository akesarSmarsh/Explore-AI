"""Unified Alert Schemas - Data Quality, Entity Type, and Smart AI alerts."""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============ Data Quality Alert Schemas ============

class DataQualityAlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    quality_type: str = Field(..., pattern="^(format_error|missing_fields|encoding_issue|size_limit|corruption|duplicate_data)$")
    file_format: Optional[str] = Field("all", pattern="^(all|csv|eml|pst|json|xml)$")
    file_size_min: Optional[int] = Field(None, ge=0)
    file_size_max: Optional[int] = Field(None, ge=0)
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class DataQualityAlertUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    quality_type: Optional[str] = Field(None, pattern="^(format_error|missing_fields|encoding_issue|size_limit|corruption|duplicate_data)$")
    file_format: Optional[str] = Field(None, pattern="^(all|csv|eml|pst|json|xml)$")
    file_size_min: Optional[int] = Field(None, ge=0)
    file_size_max: Optional[int] = Field(None, ge=0)
    severity: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    enabled: Optional[bool] = None


class DataQualityAlertResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    quality_type: str
    file_format: Optional[str]
    file_size_min: Optional[int]
    file_size_max: Optional[int]
    severity: str
    enabled: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DataQualityAlertListResponse(BaseModel):
    total: int
    alerts: List[DataQualityAlertResponse]


# ============ Entity Type Alert Schemas ============

class EntityTypeAlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    entity_type: str = Field(..., pattern="^(PERSON|ORG|GPE|MONEY|DATE|PRODUCT|EVENT|LAW|NORP|FAC|LOC|ALL)$")
    entity_value: Optional[str] = None
    detection_algorithm: str = Field("dbscan", pattern="^(dbscan|kmeans)$")
    dbscan_eps: float = Field(0.5, ge=0.1, le=5.0)
    dbscan_min_samples: int = Field(3, ge=1, le=20)
    kmeans_clusters: int = Field(3, ge=2, le=10)
    sensitivity: float = Field(1.5, ge=0.5, le=5.0)
    window_hours: int = Field(24, ge=1, le=168)
    baseline_days: int = Field(7, ge=1, le=30)
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class EntityTypeAlertUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    entity_type: Optional[str] = Field(None, pattern="^(PERSON|ORG|GPE|MONEY|DATE|PRODUCT|EVENT|LAW|NORP|FAC|LOC|ALL)$")
    entity_value: Optional[str] = None
    detection_algorithm: Optional[str] = Field(None, pattern="^(dbscan|kmeans)$")
    dbscan_eps: Optional[float] = Field(None, ge=0.1, le=5.0)
    dbscan_min_samples: Optional[int] = Field(None, ge=1, le=20)
    kmeans_clusters: Optional[int] = Field(None, ge=2, le=10)
    sensitivity: Optional[float] = Field(None, ge=0.5, le=5.0)
    window_hours: Optional[int] = Field(None, ge=1, le=168)
    baseline_days: Optional[int] = Field(None, ge=1, le=30)
    severity: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    enabled: Optional[bool] = None


class EntityTypeAlertResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    entity_type: str
    entity_value: Optional[str]
    detection_algorithm: str
    dbscan_eps: float
    dbscan_min_samples: int
    kmeans_clusters: int
    sensitivity: float
    window_hours: int
    baseline_days: int
    severity: str
    enabled: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EntityTypeAlertListResponse(BaseModel):
    total: int
    alerts: List[EntityTypeAlertResponse]


# ============ Smart AI Alert Schemas ============

class SmartAIAlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10, max_length=2000)  # Natural language description
    detection_algorithm: str = Field("dbscan", pattern="^(dbscan|kmeans)$")
    use_semantic_search: bool = True
    similarity_threshold: float = Field(0.7, ge=0.3, le=1.0)
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class SmartAIAlertUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    detection_algorithm: Optional[str] = Field(None, pattern="^(dbscan|kmeans)$")
    use_semantic_search: Optional[bool] = None
    similarity_threshold: Optional[float] = Field(None, ge=0.3, le=1.0)
    severity: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    enabled: Optional[bool] = None


class SmartAIAlertResponse(BaseModel):
    id: str
    name: str
    description: str
    generated_config: Optional[Dict[str, Any]]
    detected_entities: Optional[List[str]]
    detected_keywords: Optional[List[str]]
    detected_patterns: Optional[List[str]]
    detection_algorithm: str
    use_semantic_search: bool
    similarity_threshold: float
    severity: str
    enabled: bool
    trigger_count: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SmartAIAlertListResponse(BaseModel):
    total: int
    alerts: List[SmartAIAlertResponse]


# ============ Communication Activity Schemas ============

class CommunicationActivityData(BaseModel):
    timestamp: datetime
    email_count: int
    unique_senders: int
    unique_recipients: int
    entity_mentions: int
    is_anomaly: bool
    anomaly_type: Optional[str]
    anomaly_score: Optional[float]
    email_ids: Optional[List[str]]
    top_entities: Optional[List[Dict[str, Any]]]


class CommunicationActivityResponse(BaseModel):
    data: List[CommunicationActivityData]
    total_emails: int
    total_anomalies: int
    time_range: Dict[str, datetime]


class AnomalyDetectionResult(BaseModel):
    is_anomaly: bool
    anomaly_type: Optional[str]
    anomaly_score: float
    cluster_label: Optional[int]
    trigger_reason: Optional[str]
    current_value: float
    baseline_value: float
    affected_data_points: List[Dict[str, Any]]


class EmailDetails(BaseModel):
    id: str
    subject: Optional[str]
    sender: Optional[str]
    recipients: Optional[List[str]]
    date: Optional[datetime]
    body_preview: Optional[str]
    entities: Optional[List[Dict[str, str]]]


class DataPointEmailsResponse(BaseModel):
    timestamp: datetime
    email_count: int
    is_anomaly: bool
    anomaly_type: Optional[str]
    emails: List[EmailDetails]


# ============ Form Options ============

class UnifiedAlertFormOptions(BaseModel):
    alert_types: List[Dict[str, str]] = [
        {"value": "data_quality", "label": "Data Quality"},
        {"value": "entity_type", "label": "Entity Type"},
        {"value": "smart_ai", "label": "Smart AI"},
    ]
    
    quality_types: List[Dict[str, str]] = [
        {"value": "format_error", "label": "Format Error"},
        {"value": "missing_fields", "label": "Missing Required Fields"},
        {"value": "encoding_issue", "label": "Encoding Issue"},
        {"value": "size_limit", "label": "File Size Limit Exceeded"},
        {"value": "corruption", "label": "Data Corruption"},
        {"value": "duplicate_data", "label": "Duplicate Data"},
    ]
    
    file_formats: List[Dict[str, str]] = [
        {"value": "all", "label": "All Formats"},
        {"value": "csv", "label": "CSV Files"},
        {"value": "eml", "label": "Email Files (.eml)"},
        {"value": "pst", "label": "Outlook Files (.pst)"},
        {"value": "json", "label": "JSON Files"},
        {"value": "xml", "label": "XML Files"},
    ]
    
    entity_types: List[Dict[str, str]] = [
        {"value": "ALL", "label": "All Entities"},
        {"value": "PERSON", "label": "Person"},
        {"value": "ORG", "label": "Organization"},
        {"value": "GPE", "label": "Location (GPE)"},
        {"value": "MONEY", "label": "Money"},
        {"value": "DATE", "label": "Date"},
        {"value": "PRODUCT", "label": "Product"},
        {"value": "EVENT", "label": "Event"},
        {"value": "LAW", "label": "Law/Regulation"},
    ]
    
    detection_algorithms: List[Dict[str, str]] = [
        {"value": "dbscan", "label": "DBSCAN (Density-Based)"},
        {"value": "kmeans", "label": "K-Means Clustering"},
    ]
    
    severities: List[Dict[str, str]] = [
        {"value": "low", "label": "Low"},
        {"value": "medium", "label": "Medium"},
        {"value": "high", "label": "High"},
        {"value": "critical", "label": "Critical"},
    ]
    
    window_options: List[Dict[str, Any]] = [
        {"value": 1, "label": "1 Hour"},
        {"value": 6, "label": "6 Hours"},
        {"value": 12, "label": "12 Hours"},
        {"value": 24, "label": "24 Hours"},
        {"value": 48, "label": "48 Hours"},
        {"value": 168, "label": "1 Week"},
    ]


# ============ Dashboard Stats ============

class AlertsDashboardStats(BaseModel):
    total_data_quality_alerts: int
    total_entity_type_alerts: int
    total_smart_ai_alerts: int
    total_alerts: int
    enabled_alerts: int
    triggered_last_24h: int
    anomalies_detected: int
    by_severity: Dict[str, int]


class RecentAlert(BaseModel):
    id: str
    alert_name: str
    alert_type: str  # data_quality, entity_type, smart_ai
    triggered_at: datetime
    severity: str
    anomaly_type: Optional[str]
    trigger_reason: Optional[str]


class RecentAlertsResponse(BaseModel):
    total: int
    alerts: List[RecentAlert]


