"""Unified Alert Models - Data Quality, Entity Type, and Smart AI alerts."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class DataQualityAlert(Base):
    """Data Quality Alert - monitors file imports and data quality issues."""
    __tablename__ = "data_quality_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Data Quality specific fields
    quality_type = Column(String(50), nullable=False)  # format_error, missing_fields, encoding_issue, size_limit, corruption
    file_format = Column(String(50), nullable=True)  # csv, eml, pst, all
    file_size_min = Column(Integer, nullable=True)  # Minimum file size in bytes
    file_size_max = Column(Integer, nullable=True)  # Maximum file size in bytes
    
    # Alert configuration
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    enabled = Column(Boolean, default=True)
    
    # Tracking
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("DataQualityAlertHistory", back_populates="alert", cascade="all, delete-orphan")


class DataQualityAlertHistory(Base):
    """History of triggered Data Quality alerts."""
    __tablename__ = "data_quality_alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("data_quality_alerts.id", ondelete="CASCADE"), nullable=False)
    
    triggered_at = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String(500), nullable=True)
    error_type = Column(String(100), nullable=True)
    error_details = Column(Text, nullable=True)
    affected_records = Column(Integer, default=0)
    
    alert = relationship("DataQualityAlert", back_populates="history")


class EntityTypeAlert(Base):
    """Entity Type Alert - monitors entity mentions using DBSCAN/K-Means anomaly detection."""
    __tablename__ = "entity_type_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Entity configuration
    entity_type = Column(String(50), nullable=False)  # PERSON, ORG, GPE, MONEY, DATE, etc.
    entity_value = Column(String(255), nullable=True)  # Specific entity to monitor
    
    # Anomaly detection configuration
    detection_algorithm = Column(String(20), default="dbscan")  # dbscan, kmeans
    dbscan_eps = Column(Float, default=0.5)  # DBSCAN epsilon parameter
    dbscan_min_samples = Column(Integer, default=3)  # DBSCAN min_samples parameter
    kmeans_clusters = Column(Integer, default=3)  # K-Means number of clusters
    sensitivity = Column(Float, default=1.5)  # Sensitivity multiplier
    
    # Time window
    window_hours = Column(Integer, default=24)  # Time window for analysis
    baseline_days = Column(Integer, default=7)  # Days to use for baseline
    
    # Alert configuration
    severity = Column(String(20), default="medium")
    enabled = Column(Boolean, default=True)
    
    # Tracking
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("EntityTypeAlertHistory", back_populates="alert", cascade="all, delete-orphan")


class EntityTypeAlertHistory(Base):
    """History of triggered Entity Type alerts."""
    __tablename__ = "entity_type_alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("entity_type_alerts.id", ondelete="CASCADE"), nullable=False)
    
    triggered_at = Column(DateTime, default=datetime.utcnow)
    current_value = Column(Float, nullable=True)
    baseline_value = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    cluster_label = Column(Integer, nullable=True)  # For K-Means
    trigger_reason = Column(Text, nullable=True)
    top_entities = Column(JSON, nullable=True)  # Top contributing entities
    
    alert = relationship("EntityTypeAlert", back_populates="history")


class SmartAIAlert(Base):
    """Smart AI Alert - natural language description converted to alert rules."""
    __tablename__ = "smart_ai_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)  # User's natural language description
    
    # AI-generated configuration
    generated_config = Column(JSON, nullable=True)  # AI-parsed configuration
    detected_entities = Column(JSON, nullable=True)  # Entities detected from description
    detected_keywords = Column(JSON, nullable=True)  # Keywords detected from description
    detected_patterns = Column(JSON, nullable=True)  # Patterns detected
    
    # Anomaly detection
    detection_algorithm = Column(String(20), default="dbscan")
    use_semantic_search = Column(Boolean, default=True)  # Use embeddings for matching
    similarity_threshold = Column(Float, default=0.7)  # Semantic similarity threshold
    
    # Alert configuration
    severity = Column(String(20), default="medium")
    enabled = Column(Boolean, default=True)
    
    # Tracking
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("SmartAIAlertHistory", back_populates="alert", cascade="all, delete-orphan")


class SmartAIAlertHistory(Base):
    """History of triggered Smart AI alerts."""
    __tablename__ = "smart_ai_alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("smart_ai_alerts.id", ondelete="CASCADE"), nullable=False)
    
    triggered_at = Column(DateTime, default=datetime.utcnow)
    matched_emails = Column(JSON, nullable=True)  # List of matched email IDs
    match_scores = Column(JSON, nullable=True)  # Semantic similarity scores
    trigger_reason = Column(Text, nullable=True)
    anomaly_detected = Column(Boolean, default=False)
    anomaly_details = Column(JSON, nullable=True)
    
    alert = relationship("SmartAIAlert", back_populates="history")


class CommunicationActivity(Base):
    """Aggregated communication activity for dashboard visualization."""
    __tablename__ = "communication_activity"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, index=True)
    hour_bucket = Column(DateTime, nullable=False, index=True)  # Hourly aggregation
    
    # Metrics
    email_count = Column(Integer, default=0)
    unique_senders = Column(Integer, default=0)
    unique_recipients = Column(Integer, default=0)
    entity_mentions = Column(Integer, default=0)
    
    # Anomaly detection results
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String(100), nullable=True)  # spike, drop, silence, unusual_pattern
    anomaly_score = Column(Float, nullable=True)
    cluster_label = Column(Integer, nullable=True)
    
    # Reference data
    email_ids = Column(JSON, nullable=True)  # List of email IDs in this bucket
    top_entities = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


