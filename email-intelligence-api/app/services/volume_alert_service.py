"""Volume Alert Service for form-based alerts POC."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.volume_alert import VolumeAlert, VolumeAlertHistory
from app.models import Email, Entity
from app.schemas.volume_alert import VolumeAlertCreate, VolumeAlertUpdate


class VolumeAlertService:
    """Service for volume-based alert operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ CRUD Operations ============
    
    def create(self, data: VolumeAlertCreate) -> VolumeAlert:
        """Create a new volume alert."""
        alert = VolumeAlert(
            name=data.name,
            description=data.description,
            alert_type=data.alert_type,
            file_format=data.file_format,
            entity_type=data.entity_type,
            entity_value=data.entity_value,
            threshold_value=data.threshold_value,
            threshold_type=data.threshold_type,
            duration=data.duration,
            subscriber_emails=data.subscriber_emails,
            severity=data.severity,
            enabled=data.enabled
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get(self, alert_id: str) -> Optional[VolumeAlert]:
        """Get a volume alert by ID."""
        return self.db.query(VolumeAlert).filter(VolumeAlert.id == alert_id).first()
    
    def get_by_name(self, name: str) -> Optional[VolumeAlert]:
        """Get a volume alert by name."""
        return self.db.query(VolumeAlert).filter(VolumeAlert.name == name).first()
    
    def list(
        self,
        enabled_only: bool = False,
        alert_type: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[VolumeAlert], int]:
        """List all volume alerts."""
        query = self.db.query(VolumeAlert)
        
        if enabled_only:
            query = query.filter(VolumeAlert.enabled == True)
        
        if alert_type:
            query = query.filter(VolumeAlert.alert_type == alert_type)
        
        total = query.count()
        alerts = query.order_by(VolumeAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update(self, alert_id: str, data: VolumeAlertUpdate) -> Optional[VolumeAlert]:
        """Update a volume alert."""
        alert = self.get(alert_id)
        if not alert:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(alert, field, value)
        
        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        
        return alert
    
    def delete(self, alert_id: str) -> bool:
        """Delete a volume alert."""
        alert = self.get(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    # ============ Alert Evaluation ============
    
    def evaluate(self, alert: VolumeAlert) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate a volume alert based on current data.
        
        Returns: (triggered: bool, matched_data: dict)
        """
        duration_hours = alert.get_duration_hours()
        baseline_hours = duration_hours * 2  # Use double the duration for baseline
        
        now = datetime.utcnow()
        monitoring_start = now - timedelta(hours=duration_hours)
        baseline_start = monitoring_start - timedelta(hours=baseline_hours)
        
        # Build query for current period
        current_query = self.db.query(func.count(Entity.id)).join(Email)
        baseline_query = self.db.query(func.count(Entity.id)).join(Email)
        
        # Filter by entity type
        if alert.entity_type != "ALL":
            current_query = current_query.filter(Entity.type == alert.entity_type)
            baseline_query = baseline_query.filter(Entity.type == alert.entity_type)
        
        # Filter by specific entity value
        if alert.entity_value:
            current_query = current_query.filter(Entity.text.ilike(f"%{alert.entity_value}%"))
            baseline_query = baseline_query.filter(Entity.text.ilike(f"%{alert.entity_value}%"))
        
        # Time filters
        current_query = current_query.filter(Email.date >= monitoring_start)
        baseline_query = baseline_query.filter(
            Email.date >= baseline_start,
            Email.date < monitoring_start
        )
        
        current_volume = current_query.scalar() or 0
        baseline_volume = baseline_query.scalar() or 0
        
        # Calculate change
        triggered = False
        change_percentage = 0.0
        trigger_reason = ""
        
        if alert.alert_type == "volume_spike":
            if alert.threshold_type == "percentage":
                if baseline_volume > 0:
                    change_percentage = ((current_volume - baseline_volume) / baseline_volume) * 100
                    if change_percentage >= alert.threshold_value:
                        triggered = True
                        trigger_reason = f"Volume increased by {change_percentage:.1f}% (threshold: {alert.threshold_value}%)"
                elif current_volume > 0:
                    # No baseline, but we have current volume - significant
                    triggered = True
                    change_percentage = 100.0
                    trigger_reason = f"New activity detected: {current_volume} mentions with no baseline"
            else:  # absolute
                if current_volume >= alert.threshold_value:
                    triggered = True
                    trigger_reason = f"Volume reached {current_volume} (threshold: {alert.threshold_value})"
        
        elif alert.alert_type == "volume_threshold":
            if current_volume >= alert.threshold_value:
                triggered = True
                trigger_reason = f"Volume is {current_volume} (threshold: {alert.threshold_value})"
        
        elif alert.alert_type == "volume_drop":
            if baseline_volume > 0:
                change_percentage = ((baseline_volume - current_volume) / baseline_volume) * 100
                if change_percentage >= alert.threshold_value:
                    triggered = True
                    trigger_reason = f"Volume dropped by {change_percentage:.1f}% (threshold: {alert.threshold_value}%)"
        
        # Get sample of matched entities
        matched_entities = []
        if triggered:
            entity_query = self.db.query(Entity.text, Entity.type, func.count(Entity.id).label('count')).join(Email)
            
            if alert.entity_type != "ALL":
                entity_query = entity_query.filter(Entity.type == alert.entity_type)
            
            if alert.entity_value:
                entity_query = entity_query.filter(Entity.text.ilike(f"%{alert.entity_value}%"))
            
            entity_query = entity_query.filter(Email.date >= monitoring_start)
            entity_query = entity_query.group_by(Entity.text, Entity.type)
            entity_query = entity_query.order_by(func.count(Entity.id).desc()).limit(10)
            
            for text, etype, count in entity_query.all():
                matched_entities.append({
                    "text": text,
                    "type": etype,
                    "count": count
                })
        
        # Update last checked
        alert.last_checked_at = now
        self.db.commit()
        
        matched_data = {
            "current_volume": current_volume,
            "baseline_volume": baseline_volume,
            "change_percentage": round(change_percentage, 2),
            "trigger_reason": trigger_reason,
            "matched_entities": matched_entities,
            "monitoring_window": {
                "start": monitoring_start.isoformat(),
                "end": now.isoformat(),
                "hours": duration_hours
            }
        }
        
        # Record if triggered
        if triggered:
            self._record_trigger(alert, matched_data)
        
        return triggered, matched_data
    
    def _record_trigger(self, alert: VolumeAlert, matched_data: Dict[str, Any]) -> VolumeAlertHistory:
        """Record an alert trigger in history."""
        history = VolumeAlertHistory(
            alert_id=alert.id,
            triggered_at=datetime.utcnow(),
            current_volume=matched_data.get("current_volume", 0),
            baseline_volume=matched_data.get("baseline_volume", 0),
            change_percentage=int(matched_data.get("change_percentage", 0)),
            matched_entities=matched_data.get("matched_entities", []),
            summary=matched_data.get("trigger_reason", "")
        )
        
        self.db.add(history)
        
        # Update alert trigger count
        alert.last_triggered_at = datetime.utcnow()
        alert.trigger_count = (alert.trigger_count or 0) + 1
        
        self.db.commit()
        self.db.refresh(history)
        
        return history
    
    def evaluate_all(self) -> List[Dict[str, Any]]:
        """Evaluate all enabled alerts."""
        alerts, _ = self.list(enabled_only=True)
        triggered_alerts = []
        
        for alert in alerts:
            triggered, matched_data = self.evaluate(alert)
            if triggered:
                triggered_alerts.append({
                    "alert_id": alert.id,
                    "alert_name": alert.name,
                    "severity": alert.severity,
                    "triggered_at": datetime.utcnow().isoformat(),
                    "matched_data": matched_data
                })
        
        return triggered_alerts
    
    # ============ History ============
    
    def get_history(
        self,
        alert_id: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[VolumeAlertHistory], int]:
        """Get alert trigger history."""
        query = self.db.query(VolumeAlertHistory)
        
        if alert_id:
            query = query.filter(VolumeAlertHistory.alert_id == alert_id)
        
        total = query.count()
        history = query.order_by(VolumeAlertHistory.triggered_at.desc()).limit(limit).all()
        
        return history, total
    
    def get_triggered_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently triggered alerts."""
        history_entries = self.db.query(VolumeAlertHistory)\
            .order_by(VolumeAlertHistory.triggered_at.desc())\
            .limit(limit)\
            .all()
        
        result = []
        for h in history_entries:
            alert = self.get(h.alert_id)
            result.append({
                "history_id": h.id,
                "alert_id": h.alert_id,
                "alert_name": alert.name if alert else "Unknown",
                "severity": alert.severity if alert else "medium",
                "triggered_at": h.triggered_at.isoformat(),
                "current_volume": h.current_volume,
                "baseline_volume": h.baseline_volume,
                "change_percentage": h.change_percentage,
                "summary": h.summary
            })
        
        return result
    
    # ============ Entity Options ============
    
    def get_entity_values(self, entity_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get available entity values for dropdown."""
        query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label('count')
        )
        
        if entity_type and entity_type != "ALL":
            query = query.filter(Entity.type == entity_type)
        
        query = query.group_by(Entity.text, Entity.type)
        query = query.order_by(func.count(Entity.id).desc())
        query = query.limit(limit)
        
        return [
            {"value": text, "type": etype, "count": count}
            for text, etype, count in query.all()
        ]

