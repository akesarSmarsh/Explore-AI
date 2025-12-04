"""Anomaly Detection Service for smart alerts."""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
import statistics

from app.models import Email, Entity, SmartAlert, AlertHistory


class AnomalyService:
    """Service for anomaly detection in entity mentions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_volume_spike(
        self,
        smart_alert: SmartAlert
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check for volume spike anomaly.
        
        Args:
            smart_alert: The smart alert configuration
            
        Returns:
            Tuple of (triggered, matched_data)
        """
        config = smart_alert.anomaly_config or {}
        
        entity_type = config.get("entity_type")
        entity_value = config.get("entity_value")
        
        # Get monitoring window
        monitoring_window = config.get("monitoring_window", {"duration": 24, "unit": "hours"})
        window_hours = self._get_hours(monitoring_window)
        
        # Get baseline period
        baseline_period = config.get("baseline_period", {"duration": 7, "unit": "days"})
        baseline_hours = self._get_hours(baseline_period)
        
        # Get threshold config
        threshold = config.get("threshold", {"type": "percentage", "value": 50})
        min_baseline = config.get("min_baseline_count", 5)
        
        # Calculate current count (monitoring window)
        now = datetime.utcnow()
        window_start = now - timedelta(hours=window_hours)
        current_count = self._get_entity_count(
            entity_type, entity_value, window_start, now
        )
        
        # Calculate baseline (excluding current window)
        baseline_start = window_start - timedelta(hours=baseline_hours)
        baseline_end = window_start
        baseline_count = self._get_entity_count(
            entity_type, entity_value, baseline_start, baseline_end
        )
        
        # Calculate baseline average per window
        windows_in_baseline = baseline_hours / window_hours
        baseline_avg = baseline_count / windows_in_baseline if windows_in_baseline > 0 else 0
        
        # Skip if baseline is too low
        if baseline_avg < min_baseline:
            return False, None
        
        # Check threshold
        triggered, ratio = self._check_threshold(
            current_count, baseline_avg, threshold
        )
        
        if triggered:
            return True, {
                "alert_type": "volume_spike",
                "entity_type": entity_type,
                "entity_value": entity_value,
                "current_count": current_count,
                "baseline_avg": round(baseline_avg, 2),
                "ratio": round(ratio, 2),
                "threshold": threshold,
                "monitoring_window": monitoring_window,
                "baseline_period": baseline_period
            }
        
        return False, None
    
    def check_sudden_appearance(
        self,
        smart_alert: SmartAlert
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check for sudden appearance of new entities.
        
        Args:
            smart_alert: The smart alert configuration
            
        Returns:
            Tuple of (triggered, matched_data)
        """
        config = smart_alert.anomaly_config or {}
        
        entity_type = config.get("entity_type")
        baseline_period = config.get("baseline_period", {"duration": 30, "unit": "days"})
        baseline_hours = self._get_hours(baseline_period)
        min_mentions = config.get("min_mentions", 3)
        
        now = datetime.utcnow()
        baseline_start = now - timedelta(hours=baseline_hours)
        
        # Find entities that:
        # 1. Appeared recently (last 24 hours by default)
        # 2. Were NOT seen in the baseline period
        recent_window = timedelta(hours=24)
        recent_start = now - recent_window
        
        # Get entities from recent period
        recent_query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label("count")
        ).join(Email, Entity.email_id == Email.id)
        
        recent_query = recent_query.filter(Email.date >= recent_start)
        
        if entity_type:
            recent_query = recent_query.filter(Entity.type == entity_type)
        
        recent_query = recent_query.group_by(Entity.text, Entity.type)
        recent_query = recent_query.having(func.count(Entity.id) >= min_mentions)
        
        recent_entities = {(r.text, r.type): r.count for r in recent_query.all()}
        
        # Check which ones are new
        new_entities = []
        for (text, etype), count in recent_entities.items():
            # Check if existed in baseline
            baseline_count = self.db.query(func.count(Entity.id)).join(
                Email, Entity.email_id == Email.id
            ).filter(
                Entity.text == text,
                Entity.type == etype,
                Email.date >= baseline_start,
                Email.date < recent_start
            ).scalar() or 0
            
            if baseline_count == 0:
                new_entities.append({
                    "text": text,
                    "type": etype,
                    "count": count
                })
        
        if new_entities:
            return True, {
                "alert_type": "sudden_appearance",
                "entity_type": entity_type,
                "baseline_period": baseline_period,
                "new_entities": new_entities[:10],  # Limit to 10
                "total_new": len(new_entities)
            }
        
        return False, None
    
    def check_frequency_change(
        self,
        smart_alert: SmartAlert
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check for significant frequency change.
        
        Args:
            smart_alert: The smart alert configuration
            
        Returns:
            Tuple of (triggered, matched_data)
        """
        config = smart_alert.anomaly_config or {}
        
        entity_type = config.get("entity_type")
        entity_value = config.get("entity_value")
        
        monitoring_window = config.get("monitoring_window", {"duration": 24, "unit": "hours"})
        baseline_period = config.get("baseline_period", {"duration": 14, "unit": "days"})
        threshold = config.get("threshold", {"type": "std_deviation", "value": 2})
        min_baseline = config.get("min_baseline_count", 10)
        
        window_hours = self._get_hours(monitoring_window)
        baseline_hours = self._get_hours(baseline_period)
        
        now = datetime.utcnow()
        window_start = now - timedelta(hours=window_hours)
        baseline_start = window_start - timedelta(hours=baseline_hours)
        
        # Get current count
        current_count = self._get_entity_count(
            entity_type, entity_value, window_start, now
        )
        
        # Get historical daily counts for baseline
        daily_counts = self._get_daily_counts(
            entity_type, entity_value, baseline_start, window_start
        )
        
        if len(daily_counts) < 3 or sum(daily_counts) < min_baseline:
            return False, None
        
        # Calculate statistics
        mean = statistics.mean(daily_counts)
        std_dev = statistics.stdev(daily_counts) if len(daily_counts) > 1 else 0
        
        # Check threshold based on type
        if threshold.get("type") == "std_deviation":
            threshold_value = threshold.get("value", 2)
            upper_bound = mean + (threshold_value * std_dev)
            triggered = current_count > upper_bound
            deviation = (current_count - mean) / std_dev if std_dev > 0 else 0
        else:
            # Default to percentage
            triggered, deviation = self._check_threshold(current_count, mean, threshold)
        
        if triggered:
            return True, {
                "alert_type": "frequency_change",
                "entity_type": entity_type,
                "entity_value": entity_value,
                "current_count": current_count,
                "mean": round(mean, 2),
                "std_dev": round(std_dev, 2),
                "deviation": round(deviation, 2),
                "threshold": threshold
            }
        
        return False, None
    
    def evaluate_anomaly_alert(
        self,
        smart_alert: SmartAlert
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Evaluate an anomaly-type alert.
        
        Args:
            smart_alert: The smart alert to evaluate
            
        Returns:
            Tuple of (triggered, matched_data)
        """
        alert_type = smart_alert.alert_type
        
        if alert_type == "volume_spike":
            return self.check_volume_spike(smart_alert)
        elif alert_type == "sudden_appearance":
            return self.check_sudden_appearance(smart_alert)
        elif alert_type == "frequency_change":
            return self.check_frequency_change(smart_alert)
        
        return False, None
    
    def _get_hours(self, time_window: Dict[str, Any]) -> float:
        """Convert time window to hours."""
        duration = time_window.get("duration", 1)
        unit = time_window.get("unit", "hours")
        
        if unit == "hours":
            return duration
        elif unit == "days":
            return duration * 24
        elif unit == "weeks":
            return duration * 24 * 7
        
        return duration
    
    def _get_entity_count(
        self,
        entity_type: Optional[str],
        entity_value: Optional[str],
        start: datetime,
        end: datetime
    ) -> int:
        """Get entity count for a time period."""
        query = self.db.query(func.count(Entity.id)).join(
            Email, Entity.email_id == Email.id
        )
        
        query = query.filter(Email.date >= start)
        query = query.filter(Email.date <= end)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text == entity_value)
        
        return query.scalar() or 0
    
    def _get_daily_counts(
        self,
        entity_type: Optional[str],
        entity_value: Optional[str],
        start: datetime,
        end: datetime
    ) -> List[int]:
        """Get daily entity counts for a period."""
        query = self.db.query(
            func.date(Email.date).label("day"),
            func.count(Entity.id).label("count")
        ).join(Entity, Entity.email_id == Email.id)
        
        query = query.filter(Email.date >= start)
        query = query.filter(Email.date <= end)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(func.date(Email.date))
        
        return [r.count for r in query.all()]
    
    def _check_threshold(
        self,
        current: float,
        baseline: float,
        threshold: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Check if current value exceeds threshold relative to baseline.
        
        Returns:
            Tuple of (triggered, ratio/percentage)
        """
        threshold_type = threshold.get("type", "percentage")
        threshold_value = threshold.get("value", 50)
        
        if baseline == 0:
            return current > 0, float("inf") if current > 0 else 0
        
        ratio = current / baseline
        
        if threshold_type == "percentage":
            percentage_increase = (current - baseline) / baseline * 100
            return percentage_increase >= threshold_value, percentage_increase
        
        elif threshold_type == "multiplier":
            return ratio >= threshold_value, ratio
        
        elif threshold_type == "absolute":
            return current >= threshold_value, current
        
        elif threshold_type == "std_deviation":
            # For std_deviation, caller should handle separately
            return False, ratio
        
        return False, ratio










