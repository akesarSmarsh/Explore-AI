"""Email service for business logic."""
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, or_

from app.models import Email, Entity, Alert
from app.schemas.email import EmailCreate, EmailFilters, EmailResponse, EmailDetailResponse
from app.core.ner_processor import ner_processor
from app.core.embeddings import embedding_processor
from app.core.vector_store import vector_store


class EmailService:
    """Service for email operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_email(self, email_data: EmailCreate, process_ner: bool = True) -> Email:
        """
        Create a new email with NER processing.
        
        Args:
            email_data: Email data
            process_ner: Whether to run NER extraction
            
        Returns:
            Created Email object
        """
        # Create email record
        email = Email(
            message_id=email_data.message_id,
            subject=email_data.subject,
            sender=email_data.sender,
            recipients=json.dumps(email_data.recipients) if email_data.recipients else "[]",
            cc=json.dumps(email_data.cc) if email_data.cc else "[]",
            date=email_data.date,
            body=email_data.body,
            raw_file_path=email_data.raw_file_path
        )
        
        self.db.add(email)
        self.db.flush()  # Get the ID
        
        # Process NER
        if process_ner and email_data.body:
            entities = ner_processor.extract_entities(email_data.body)
            for ent_data in entities:
                entity = Entity(
                    email_id=email.id,
                    text=ent_data["text"],
                    type=ent_data["type"],
                    start_pos=ent_data["start_pos"],
                    end_pos=ent_data["end_pos"],
                    sentence=ent_data.get("sentence")
                )
                self.db.add(entity)
            
            # Generate embedding
            embedding = embedding_processor.encode(email_data.body)
            metadata = {
                "subject": email_data.subject or "",
                "sender": email_data.sender or "",
                "date": email_data.date.isoformat() if email_data.date else ""
            }
            vector_store.add_embedding(
                id=email.id,
                embedding=embedding,
                metadata=metadata,
                document=email_data.body[:1000]  # Store first 1000 chars
            )
        
        self.db.commit()
        return email
    
    def get_email(self, email_id: str) -> Optional[Email]:
        """Get email by ID."""
        return self.db.query(Email).filter(Email.id == email_id).first()
    
    def get_email_detail(self, email_id: str) -> Optional[EmailDetailResponse]:
        """Get detailed email with entities and alerts."""
        email = self.get_email(email_id)
        if not email:
            return None
        
        # Parse recipients and cc
        recipients = json.loads(email.recipients) if email.recipients else []
        cc = json.loads(email.cc) if email.cc else []
        
        # Get all entities with positions (for highlighting)
        all_entities = [
            {
                "text": e.text,
                "type": e.type,
                "start": e.start_pos,
                "end": e.end_pos,
                "sentence": e.sentence
            }
            for e in email.entities
        ]
        
        # Get highlighted body using all entity positions
        body_html = None
        if email.body and all_entities:
            body_html = ner_processor.highlight_entities_html(email.body, all_entities)
        
        # Deduplicate entities for display (unique text+type combinations)
        seen_entities = set()
        entities = []
        for e in email.entities:
            key = (e.text.lower().strip(), e.type)
            if key not in seen_entities:
                seen_entities.add(key)
                entities.append({
                    "text": e.text,
                    "type": e.type,
                    "start": e.start_pos,
                    "end": e.end_pos,
                    "sentence": e.sentence
                })
        
        # Get alerts
        alerts = []
        for alert in email.alerts:
            alerts.append({
                "id": alert.id,
                "rule_name": alert.rule.name if alert.rule else "Unknown",
                "severity": alert.severity,
                "matched_entity": alert.matched_text
            })
        
        # Get similar emails
        similar = vector_store.find_similar(email_id, n_results=5)
        similar_ids = [s["id"] for s in similar]
        
        return EmailDetailResponse(
            id=email.id,
            message_id=email.message_id,
            subject=email.subject,
            sender=email.sender,
            recipients=recipients,
            cc=cc,
            date=email.date,
            body=email.body,
            body_html=body_html,
            entities=entities,
            alerts=alerts,
            similar_emails=similar_ids
        )
    
    def list_emails(self, filters: EmailFilters) -> Tuple[List[EmailResponse], int]:
        """
        List emails with filters and pagination.
        
        Args:
            filters: Filter parameters
            
        Returns:
            Tuple of (emails list, total count)
        """
        query = self.db.query(Email)
        
        # Apply filters
        if filters.date_from:
            query = query.filter(Email.date >= filters.date_from)
        if filters.date_to:
            query = query.filter(Email.date <= filters.date_to)
        if filters.sender:
            query = query.filter(Email.sender.ilike(f"%{filters.sender}%"))
        
        # Filter by entity
        if filters.entity_type or filters.entity_value:
            entity_query = self.db.query(Entity.email_id)
            if filters.entity_type:
                entity_query = entity_query.filter(Entity.type == filters.entity_type)
            if filters.entity_value:
                entity_query = entity_query.filter(Entity.text.ilike(f"%{filters.entity_value}%"))
            email_ids = [e[0] for e in entity_query.distinct().all()]
            query = query.filter(Email.id.in_(email_ids))
        
        # Filter by alert
        if filters.has_alert is not None:
            if filters.has_alert:
                query = query.filter(Email.alerts.any())
            else:
                query = query.filter(~Email.alerts.any())
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if filters.sort_by == "date":
            order_col = Email.date
        elif filters.sort_by == "sender":
            order_col = Email.sender
        else:
            order_col = Email.date
        
        if filters.sort_order == "desc":
            query = query.order_by(desc(order_col))
        else:
            query = query.order_by(asc(order_col))
        
        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        emails = query.offset(offset).limit(filters.limit).all()
        
        # Format response
        results = []
        for email in emails:
            recipients = json.loads(email.recipients) if email.recipients else []
            
            # Count entities by type
            entity_counts = {}
            for entity in email.entities:
                entity_counts[entity.type] = entity_counts.get(entity.type, 0) + 1
            
            preview = email.body[:200] if email.body else None
            
            results.append(EmailResponse(
                id=email.id,
                subject=email.subject,
                sender=email.sender,
                recipients=recipients,
                date=email.date,
                preview=preview,
                entity_counts=entity_counts,
                alert_count=len(email.alerts)
            ))
        
        return results, total
    
    def delete_email(self, email_id: str) -> bool:
        """Delete an email."""
        email = self.get_email(email_id)
        if not email:
            return False
        
        # Delete from vector store
        vector_store.delete([email_id])
        
        # Delete from database
        self.db.delete(email)
        self.db.commit()
        return True
    
    def get_email_count(self) -> int:
        """Get total email count."""
        return self.db.query(func.count(Email.id)).scalar()

