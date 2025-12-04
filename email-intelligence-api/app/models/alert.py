"""Alert and AlertRule SQLAlchemy models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class SeverityLevel(str, enum.Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


class AlertRule(Base):
    """Alert rule database model."""
    
    __tablename__ = "alert_rules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default=SeverityLevel.MEDIUM.value)
    enabled = Column(Boolean, default=True)
    conditions = Column(Text, nullable=False)  # JSON object defining rule conditions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AlertRule(id={self.id}, name='{self.name}')>"


class Alert(Base):
    """Triggered alert database model."""
    
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("alert_rules.id"), nullable=False, index=True)
    email_id = Column(String(36), ForeignKey("emails.id"), nullable=False, index=True)
    entity_id = Column(String(36), ForeignKey("entities.id"), nullable=True, index=True)
    severity = Column(String(20), default=SeverityLevel.MEDIUM.value)
    status = Column(String(20), default=AlertStatus.ACTIVE.value, index=True)
    matched_text = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    email = relationship("Email", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, rule_id={self.rule_id}, status='{self.status}')>"

