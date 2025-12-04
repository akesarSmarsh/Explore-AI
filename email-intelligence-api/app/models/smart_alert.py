"""Smart Alert and Alert History SQLAlchemy models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class SmartAlert(Base):
    """Enhanced Smart Alert database model with anomaly detection support."""
    
    __tablename__ = "smart_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Alert type: entity_threshold, entity_mention, keyword_match, 
    #             co_occurrence, pattern_match, volume_spike, 
    #             sudden_appearance, frequency_change
    alert_type = Column(String(50), nullable=False, index=True)
    
    # Conditions for standard alerts (JSON)
    conditions = Column(JSON, nullable=True)
    
    # Anomaly detection configuration (JSON)
    # {
    #   "entity_type": "PERSON",
    #   "entity_value": null,
    #   "monitoring_window": {"duration": 24, "unit": "hours"},
    #   "baseline_period": {"duration": 7, "unit": "days"},
    #   "threshold": {"type": "percentage", "value": 50},
    #   "min_baseline_count": 10
    # }
    anomaly_config = Column(JSON, nullable=True)
    
    # Optional filters to narrow scope
    # {"senders": [], "date_range": "last_7_days"}
    filters = Column(JSON, nullable=True)
    
    # Schedule configuration (JSON)
    # {"type": "realtime|scheduled", "frequency": "hourly|daily|weekly", "time": "09:00"}
    schedule = Column(JSON, nullable=True)
    
    # Notification configuration (JSON)
    # {"email": {"enabled": true, "recipients": [], "subject_template": ""}}
    notifications = Column(JSON, nullable=True)
    
    # Alert settings
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    enabled = Column(Boolean, default=True, index=True)
    
    # Tracking
    last_checked_at = Column(DateTime, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("AlertHistory", back_populates="smart_alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SmartAlert(id={self.id}, name='{self.name}', type='{self.alert_type}')>"


class AlertHistory(Base):
    """Alert trigger history for tracking."""
    
    __tablename__ = "alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    smart_alert_id = Column(String(36), ForeignKey("smart_alerts.id"), nullable=False, index=True)
    
    # Optional reference to triggering email (null for aggregate/anomaly alerts)
    email_id = Column(String(36), ForeignKey("emails.id"), nullable=True, index=True)
    
    # When triggered
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # What matched (JSON)
    # {"entity": "Ken Lay", "type": "PERSON", "count": 150, "baseline": 50}
    matched_data = Column(JSON, nullable=True)
    
    # Context/summary
    summary = Column(Text, nullable=True)
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False)
    notification_status = Column(String(50), nullable=True)  # sent, failed, pending
    notification_error = Column(Text, nullable=True)
    
    # Relationships
    smart_alert = relationship("SmartAlert", back_populates="history")
    email = relationship("Email", foreign_keys=[email_id])
    notifications = relationship("EmailNotification", back_populates="alert_history", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AlertHistory(id={self.id}, alert_id={self.smart_alert_id}, triggered_at={self.triggered_at})>"


class EmailNotification(Base):
    """Email notification tracking."""
    
    __tablename__ = "email_notifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_history_id = Column(String(36), ForeignKey("alert_history.id"), nullable=False, index=True)
    
    # Email details
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    alert_history = relationship("AlertHistory", back_populates="notifications")
    
    def __repr__(self):
        return f"<EmailNotification(id={self.id}, recipient='{self.recipient}', status='{self.status}')>"










