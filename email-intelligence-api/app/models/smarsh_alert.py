"""Smarsh Alert SQLAlchemy models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SmarshAlert(Base):
    """Enhanced Smarsh Alert database model."""
    
    __tablename__ = "smarsh_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Alert type: static (threshold) or smart (anomaly)
    alert_type = Column(String(20), nullable=False, default="static", index=True)
    
    # Metric configuration (JSON)
    # {"metric_type": "email_volume", "entity_type": "PERSON", "keywords": [...]}
    metric = Column(JSON, nullable=False)
    
    # Filter configuration (JSON)
    # {"sender_domains": [...], "entity_types": [...], "date_from": ..., "date_to": ...}
    filters = Column(JSON, nullable=True)
    
    # Time window configuration (JSON)
    # {"window_size": 1, "window_unit": "days", "check_frequency": 5, "baseline_days": 7}
    time_window = Column(JSON, nullable=False)
    
    # Threshold configuration for static alerts (JSON)
    # {"operator": "greater_than", "value": 100}
    threshold = Column(JSON, nullable=True)
    
    # Anomaly configuration for smart alerts (JSON)
    # {"algorithm": "zscore", "zscore_threshold": 2.5, "min_baseline_count": 10}
    anomaly = Column(JSON, nullable=True)
    
    # Cooldown / anti-spam configuration (JSON)
    # {"enabled": true, "cooldown_minutes": 60, "max_alerts_per_day": 10, "consecutive_anomalies": 1}
    cooldown = Column(JSON, nullable=False)
    
    # Notification configuration (JSON)
    # {"email_enabled": true, "email_recipients": [...], "webhook_url": ...}
    notifications = Column(JSON, nullable=False)
    
    # Alert settings
    severity = Column(String(20), default="medium")
    enabled = Column(Boolean, default=True, index=True)
    
    # Tracking - evaluation state
    last_checked_at = Column(DateTime, nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    
    # Anti-spam tracking
    alerts_today = Column(Integer, default=0)
    alerts_today_date = Column(DateTime, nullable=True)  # To reset daily count
    consecutive_anomaly_count = Column(Integer, default=0)  # For longevity
    
    # Last computed values (for dashboard display)
    last_value = Column(Float, nullable=True)
    last_baseline = Column(Float, nullable=True)
    last_zscore = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("SmarshAlertHistory", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SmarshAlert(id={self.id}, name='{self.name}', type='{self.alert_type}')>"
    
    def get_window_minutes(self) -> int:
        """Convert window config to minutes."""
        tw = self.time_window or {}
        size = tw.get("window_size", 1)
        unit = tw.get("window_unit", "days")
        
        multipliers = {"minutes": 1, "hours": 60, "days": 1440}
        return size * multipliers.get(unit, 1440)
    
    def reset_daily_count_if_needed(self):
        """Reset daily alert count if it's a new day."""
        today = datetime.utcnow().date()
        if self.alerts_today_date is None or self.alerts_today_date.date() != today:
            self.alerts_today = 0
            self.alerts_today_date = datetime.utcnow()


class SmarshAlertHistory(Base):
    """Alert trigger history with detailed metrics."""
    
    __tablename__ = "smarsh_alert_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("smarsh_alerts.id"), nullable=False, index=True)
    
    # When triggered
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Metric values at trigger time
    metric_value = Column(Float, default=0)
    baseline_value = Column(Float, default=0)
    zscore = Column(Float, nullable=True)
    percentage_change = Column(Float, nullable=True)
    
    # What caused the trigger
    trigger_reason = Column(Text, nullable=True)
    
    # Top contributors (JSON array)
    # [{"entity": "Ken Lay", "count": 50}, ...]
    top_contributors = Column(JSON, nullable=True)
    
    # Time series snapshot (JSON)
    # [{"timestamp": "...", "value": 10}, ...]
    time_series_snapshot = Column(JSON, nullable=True)
    
    # Notification tracking
    notification_sent = Column(Boolean, default=False)
    notification_status = Column(String(50), nullable=True)
    notification_error = Column(Text, nullable=True)
    
    # Relationships
    alert = relationship("SmarshAlert", back_populates="history")
    
    def __repr__(self):
        return f"<SmarshAlertHistory(id={self.id}, alert_id={self.alert_id}, triggered_at={self.triggered_at})>"
