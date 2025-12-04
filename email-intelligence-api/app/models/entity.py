"""Entity SQLAlchemy model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Entity(Base):
    """Named Entity database model."""
    
    __tablename__ = "entities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email_id = Column(String(36), ForeignKey("emails.id"), nullable=False, index=True)
    text = Column(String(500), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # PERSON, ORG, MONEY, DATE, GPE, etc.
    start_pos = Column(Integer, nullable=False)
    end_pos = Column(Integer, nullable=False)
    sentence = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="entities")
    
    def __repr__(self):
        return f"<Entity(id={self.id}, text='{self.text}', type='{self.type}')>"

