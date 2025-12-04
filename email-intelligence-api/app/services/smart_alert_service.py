"""Smart Alert Service for CRUD and evaluation."""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import SmartAlert, AlertHistory, Email, Entity, EmailNotification
from app.schemas.smart_alert import SmartAlertCreate, SmartAlertUpdate
from app.services.anomaly_service import AnomalyService


class SmartAlertService:
    """Service for smart alert operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.anomaly_service = AnomalyService(db)
    
    # ============ CRUD Operations ============
    
    def create(self, data: SmartAlertCreate) -> SmartAlert:
        """Create a new smart alert."""
        alert = SmartAlert(
            name=data.name,
            description=data.description,
            alert_type=data.alert_type,
            conditions=data.conditions,
            anomaly_config=data.anomaly_config.model_dump() if data.anomaly_config else None,
            filters=data.filters,
            schedule=data.schedule.model_dump() if data.schedule else None,
            notifications=data.notifications.model_dump() if data.notifications else None,
            severity=data.severity,
            enabled=data.enabled
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get(self, alert_id: str) -> Optional[SmartAlert]:
        """Get a smart alert by ID."""
        return self.db.query(SmartAlert).filter(SmartAlert.id == alert_id).first()
    
    def get_by_name(self, name: str) -> Optional[SmartAlert]:
        """Get a smart alert by name."""
        return self.db.query(SmartAlert).filter(SmartAlert.name == name).first()
    
    def list(
        self,
        enabled_only: bool = False,
        alert_type: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[SmartAlert], int]:
        """List smart alerts."""
        query = self.db.query(SmartAlert)
        
        if enabled_only:
            query = query.filter(SmartAlert.enabled == True)
        if alert_type:
            query = query.filter(SmartAlert.alert_type == alert_type)
        
        total = query.count()
        alerts = query.order_by(SmartAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update(self, alert_id: str, data: SmartAlertUpdate) -> Optional[SmartAlert]:
        """Update a smart alert."""
        alert = self.get(alert_id)
        if not alert:
            return None
        
        if data.name is not None:
            alert.name = data.name
        if data.description is not None:
            alert.description = data.description
        if data.alert_type is not None:
            alert.alert_type = data.alert_type
        if data.conditions is not None:
            alert.conditions = data.conditions
        if data.anomaly_config is not None:
            alert.anomaly_config = data.anomaly_config.model_dump()
        if data.filters is not None:
            alert.filters = data.filters
        if data.schedule is not None:
            alert.schedule = data.schedule.model_dump()
        if data.notifications is not None:
            alert.notifications = data.notifications.model_dump()
        if data.severity is not None:
            alert.severity = data.severity
        if data.enabled is not None:
            alert.enabled = data.enabled
        
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def delete(self, alert_id: str) -> bool:
        """Delete a smart alert."""
        alert = self.get(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    # ============ Alert Evaluation ============
    
    def evaluate(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate a smart alert.
        
        Returns:
            Tuple of (triggered, matched_data)
        """
        if not alert.enabled:
            return False, None
        
        alert_type = alert.alert_type
        
        # Anomaly detection types
        if alert_type in ["volume_spike", "sudden_appearance", "frequency_change"]:
            return self.anomaly_service.evaluate_anomaly_alert(alert)
        
        # Standard alert types
        if alert_type == "entity_threshold":
            return self._eval_entity_threshold(alert)
        elif alert_type == "entity_mention":
            return self._eval_entity_mention(alert)
        elif alert_type == "keyword_match":
            return self._eval_keyword_match(alert)
        elif alert_type == "co_occurrence":
            return self._eval_co_occurrence(alert)
        elif alert_type == "pattern_match":
            return self._eval_pattern_match(alert)
        
        return False, None
    
    def evaluate_all(self, scheduled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Evaluate all enabled alerts.
        
        Args:
            scheduled_only: Only evaluate scheduled alerts
            
        Returns:
            List of triggered alerts with details
        """
        query = self.db.query(SmartAlert).filter(SmartAlert.enabled == True)
        
        if scheduled_only:
            # Filter for alerts with scheduled type
            # This is simplified - would need proper JSON query in production
            pass
        
        alerts = query.all()
        triggered = []
        
        for alert in alerts:
            is_triggered, matched_data = self.evaluate(alert)
            
            if is_triggered:
                # Create history record
                history = self._create_history(alert, matched_data)
                
                triggered.append({
                    "alert_id": alert.id,
                    "alert_name": alert.name,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "matched_data": matched_data,
                    "history_id": history.id
                })
                
                # Update alert tracking
                alert.last_triggered_at = datetime.utcnow()
                alert.trigger_count += 1
            
            alert.last_checked_at = datetime.utcnow()
        
        self.db.commit()
        return triggered
    
    def _create_history(
        self,
        alert: SmartAlert,
        matched_data: Dict[str, Any],
        email_id: Optional[str] = None
    ) -> AlertHistory:
        """Create an alert history record."""
        summary = self._generate_summary(alert, matched_data)
        
        history = AlertHistory(
            smart_alert_id=alert.id,
            email_id=email_id,
            matched_data=matched_data,
            summary=summary,
            notification_sent=False
        )
        
        self.db.add(history)
        self.db.flush()
        return history
    
    def _generate_summary(self, alert: SmartAlert, matched_data: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        alert_type = alert.alert_type
        
        if alert_type == "volume_spike":
            current = matched_data.get("current_count", 0)
            baseline = matched_data.get("baseline_avg", 0)
            entity = matched_data.get("entity_type", "entities")
            return f"Volume spike detected: {current} {entity} mentions (baseline: {baseline})"
        
        elif alert_type == "sudden_appearance":
            count = matched_data.get("total_new", 0)
            return f"New entities detected: {count} entities appeared for the first time"
        
        elif alert_type == "frequency_change":
            entity = matched_data.get("entity_value") or matched_data.get("entity_type", "entities")
            deviation = matched_data.get("deviation", 0)
            return f"Frequency change detected for {entity}: {deviation:.1f} std devs above mean"
        
        elif alert_type == "entity_mention":
            entities = matched_data.get("matched_entities", [])
            return f"Entity mentioned: {', '.join(entities[:3])}"
        
        return f"Alert '{alert.name}' triggered"
    
    # ============ Standard Alert Evaluations ============
    
    def _eval_entity_threshold(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate entity threshold condition."""
        conditions = alert.conditions or {}
        entity_type = conditions.get("entity_type", "MONEY")
        operator = conditions.get("operator", "greater_than")
        threshold = conditions.get("value", 0)
        
        # Get recent emails with this entity type
        recent_emails = self._get_recent_emails(alert.filters)
        
        matches = []
        for email in recent_emails:
            for entity in email.entities:
                if entity.type != entity_type:
                    continue
                
                value = self._extract_numeric_value(entity.text)
                if value is None:
                    continue
                
                triggered = False
                if operator == "greater_than" and value > threshold:
                    triggered = True
                elif operator == "less_than" and value < threshold:
                    triggered = True
                elif operator == "equals" and value == threshold:
                    triggered = True
                
                if triggered:
                    matches.append({
                        "email_id": email.id,
                        "entity": entity.text,
                        "value": value
                    })
        
        if matches:
            return True, {
                "alert_type": "entity_threshold",
                "matches": matches[:10],
                "total_matches": len(matches)
            }
        
        return False, None
    
    def _eval_entity_mention(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate entity mention condition."""
        conditions = alert.conditions or {}
        target_entities = [e.lower() for e in conditions.get("entities", [])]
        match_type = conditions.get("match_type", "exact")
        
        if not target_entities:
            return False, None
        
        recent_emails = self._get_recent_emails(alert.filters)
        
        matches = []
        matched_entities = set()
        
        for email in recent_emails:
            for entity in email.entities:
                entity_lower = entity.text.lower()
                
                if match_type == "exact":
                    if entity_lower in target_entities:
                        matches.append({"email_id": email.id, "entity": entity.text})
                        matched_entities.add(entity.text)
                else:  # contains
                    for target in target_entities:
                        if target in entity_lower:
                            matches.append({"email_id": email.id, "entity": entity.text})
                            matched_entities.add(entity.text)
                            break
        
        if matches:
            return True, {
                "alert_type": "entity_mention",
                "matched_entities": list(matched_entities),
                "matches": matches[:10],
                "total_matches": len(matches)
            }
        
        return False, None
    
    def _eval_keyword_match(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate keyword match condition."""
        conditions = alert.conditions or {}
        keywords = [k.lower() for k in conditions.get("keywords", [])]
        match_all = conditions.get("match_all", False)
        
        if not keywords:
            return False, None
        
        recent_emails = self._get_recent_emails(alert.filters)
        
        matches = []
        for email in recent_emails:
            body_lower = (email.body or "").lower()
            subject_lower = (email.subject or "").lower()
            text = body_lower + " " + subject_lower
            
            found_keywords = [k for k in keywords if k in text]
            
            if match_all:
                triggered = len(found_keywords) == len(keywords)
            else:
                triggered = len(found_keywords) > 0
            
            if triggered:
                matches.append({
                    "email_id": email.id,
                    "subject": email.subject,
                    "keywords_found": found_keywords
                })
        
        if matches:
            return True, {
                "alert_type": "keyword_match",
                "keywords": keywords,
                "matches": matches[:10],
                "total_matches": len(matches)
            }
        
        return False, None
    
    def _eval_co_occurrence(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate entity co-occurrence condition."""
        conditions = alert.conditions or {}
        type1 = conditions.get("entity_type_1")
        type2 = conditions.get("entity_type_2")
        same_sentence = conditions.get("same_sentence", True)
        
        if not type1 or not type2:
            return False, None
        
        recent_emails = self._get_recent_emails(alert.filters)
        
        matches = []
        for email in recent_emails:
            entities_type1 = [e for e in email.entities if e.type == type1]
            entities_type2 = [e for e in email.entities if e.type == type2]
            
            if not entities_type1 or not entities_type2:
                continue
            
            for e1 in entities_type1:
                for e2 in entities_type2:
                    if same_sentence:
                        if e1.sentence and e2.sentence and e1.sentence == e2.sentence:
                            matches.append({
                                "email_id": email.id,
                                "entity1": e1.text,
                                "entity2": e2.text,
                                "sentence": e1.sentence[:200]
                            })
                    else:
                        matches.append({
                            "email_id": email.id,
                            "entity1": e1.text,
                            "entity2": e2.text
                        })
        
        if matches:
            return True, {
                "alert_type": "co_occurrence",
                "entity_types": [type1, type2],
                "matches": matches[:10],
                "total_matches": len(matches)
            }
        
        return False, None
    
    def _eval_pattern_match(self, alert: SmartAlert) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Evaluate regex pattern match condition."""
        conditions = alert.conditions or {}
        pattern = conditions.get("pattern")
        field = conditions.get("field", "body")
        
        if not pattern:
            return False, None
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return False, None
        
        recent_emails = self._get_recent_emails(alert.filters)
        
        matches = []
        for email in recent_emails:
            if field == "subject":
                text = email.subject or ""
            elif field == "sender":
                text = email.sender or ""
            else:
                text = email.body or ""
            
            found = regex.findall(text)
            if found:
                matches.append({
                    "email_id": email.id,
                    "matches": found[:5]
                })
        
        if matches:
            return True, {
                "alert_type": "pattern_match",
                "pattern": pattern,
                "field": field,
                "matches": matches[:10],
                "total_matches": len(matches)
            }
        
        return False, None
    
    def _get_recent_emails(self, filters: Optional[Dict[str, Any]] = None, limit: int = 1000) -> List[Email]:
        """Get recent emails based on filters."""
        from datetime import timedelta
        
        query = self.db.query(Email)
        
        if filters:
            date_range = filters.get("date_range")
            if date_range:
                now = datetime.utcnow()
                if date_range == "last_24_hours":
                    query = query.filter(Email.date >= now - timedelta(hours=24))
                elif date_range == "last_7_days":
                    query = query.filter(Email.date >= now - timedelta(days=7))
                elif date_range == "last_30_days":
                    query = query.filter(Email.date >= now - timedelta(days=30))
            
            senders = filters.get("senders")
            if senders:
                query = query.filter(Email.sender.in_(senders))
        
        return query.order_by(Email.date.desc()).limit(limit).all()
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text."""
        text = text.lower().replace(",", "").replace("$", "").strip()
        
        multiplier = 1
        if "billion" in text:
            multiplier = 1_000_000_000
            text = text.replace("billion", "").strip()
        elif "million" in text:
            multiplier = 1_000_000
            text = text.replace("million", "").strip()
        elif "thousand" in text:
            multiplier = 1_000
            text = text.replace("thousand", "").strip()
        
        match = re.search(r'[\d.]+', text)
        if match:
            try:
                return float(match.group()) * multiplier
            except ValueError:
                pass
        
        return None
    
    # ============ History Operations ============
    
    def get_history(
        self,
        alert_id: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[AlertHistory], int]:
        """Get alert history."""
        query = self.db.query(AlertHistory)
        
        if alert_id:
            query = query.filter(AlertHistory.smart_alert_id == alert_id)
        
        total = query.count()
        history = query.order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
        
        return history, total
    
    def get_triggered_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently triggered alerts with details."""
        history = self.db.query(AlertHistory).join(SmartAlert).order_by(
            AlertHistory.triggered_at.desc()
        ).limit(limit).all()
        
        results = []
        for h in history:
            results.append({
                "id": h.id,
                "smart_alert_id": h.smart_alert_id,
                "smart_alert_name": h.smart_alert.name if h.smart_alert else None,
                "email_id": h.email_id,
                "email_subject": h.email.subject if h.email else None,
                "triggered_at": h.triggered_at,
                "matched_data": h.matched_data,
                "summary": h.summary,
                "notification_sent": h.notification_sent,
                "notification_status": h.notification_status
            })
        
        return results










