"""Volume Alert SQLAlchemy model for form-based alerts."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class VolumeAlert(Base):
    """Volume-based Alert database model - simplified form-based alerts."""
    
    __tablename__ = "volume_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Alert type: volume_spike, volume_threshold, volume_drop
    alert_type = Column(String(50), nullable=False, default="volume_spike", index=True)
    
    # File format filter
    file_format = Column(String(20), default="all")  # csv, eml, pst, all
    
    # Entity configuration
    entity_type = Column(String(50), nullable=False, default="ALL", index=True)  # PERSON, ORG, GPE, etc.
    entity_value = Column(String(500), nullable=True)  # Specific entity to monitor
    
    # Threshold settings
    threshold_value = Column(Integer, default=50)  # Threshold value
    threshold_type = Column(String(20), default="percentage")  # percentage, absolute
    
    # Monitoring duration
    duration = Column(String(20), default="1_day")  # 1_day, 2_days, 3_days, 7_days
    
    # Subscriber emails (stored as JSON array)
    subscriber_emails = Column(JSON, default=list)
    
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
    trigger_history = relationship("VolumeAlertHistory", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VolumeAlert(id={self.id}, name='{self.name}', type='{self.alert_type}')>"
    
    def get_duration_hours(self) -> int:
        """Convert duration string to hours."""
        duration_map = {
            "1_day": 24,
            "2_days": 48,
            "3_days": 72,
            "7_days": 168
        }
        return duration_map.get(self.duration, 24)


class VolumeAlertHistory(Base):
    """Volume alert trigger history."""
    
    __tablename__ = "volume_alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("volume_alerts.id"), nullable=False, index=True)
    
    # Trigger details
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    current_volume = Column(Integer, default=0)
    baseline_volume = Column(Integer, default=0)
    change_percentage = Column(Integer, default=0)
    
    # Matched data (JSON)
    matched_entities = Column(JSON, nullable=True)
    
    # Summary
    summary = Column(Text, nullable=True)
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False)
    notification_status = Column(String(50), nullable=True)  # sent, failed, pending
    
    # Relationships
    alert = relationship("VolumeAlert", back_populates="trigger_history")
    
    def __repr__(self):
        return f"<VolumeAlertHistory(id={self.id}, alert_id={self.alert_id}, triggered_at={self.triggered_at})>"

