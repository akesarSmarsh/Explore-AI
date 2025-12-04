"""Email SQLAlchemy model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class Email(Base):
    """Email database model."""
    
    __tablename__ = "emails"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(255), unique=True, nullable=True, index=True)
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=True, index=True)
    recipients = Column(Text, nullable=True)  # JSON array
    cc = Column(Text, nullable=True)  # JSON array
    date = Column(DateTime, nullable=True, index=True)
    body = Column(Text, nullable=True)
    raw_file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    entities = relationship("Entity", back_populates="email", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="email", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Email(id={self.id}, subject='{self.subject[:50] if self.subject else 'N/A'}')>"

