"""Smarsh Alert Service with anomaly detection."""
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.smarsh_alert import SmarshAlert, SmarshAlertHistory
from app.models import Email, Entity
from app.schemas.smarsh_alert import SmarshAlertCreate, SmarshAlertUpdate


class SmarshAlertService:
    """Service for Smarsh alert operations with anomaly detection."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest_email_date(self) -> datetime:
        """
        Get the latest email date from the database.
        Falls back to current time if no emails exist.
        This ensures alert evaluation works with historical data.
        """
        result = self.db.query(func.max(Email.date)).scalar()
        if result:
            return result
        return datetime.utcnow()
    
    # ============ CRUD Operations ============
    
    def create(self, data: SmarshAlertCreate) -> SmarshAlert:
        """Create a new Smarsh alert."""
        alert = SmarshAlert(
            name=data.name,
            description=data.description,
            alert_type=data.alert_type,
            metric=data.metric.model_dump(),
            filters=data.filters.model_dump() if data.filters else None,
            time_window=data.time_window.model_dump(),
            threshold=data.threshold.model_dump() if data.threshold else None,
            anomaly=data.anomaly.model_dump() if data.anomaly else None,
            cooldown=data.cooldown.model_dump(),
            notifications=data.notifications.model_dump(),
            severity=data.severity,
            enabled=data.enabled
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get(self, alert_id: str) -> Optional[SmarshAlert]:
        """Get an alert by ID."""
        return self.db.query(SmarshAlert).filter(SmarshAlert.id == alert_id).first()
    
    def get_by_name(self, name: str) -> Optional[SmarshAlert]:
        """Get an alert by name."""
        return self.db.query(SmarshAlert).filter(SmarshAlert.name == name).first()
    
    def list(
        self,
        enabled_only: bool = False,
        alert_type: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[SmarshAlert], int]:
        """List all alerts."""
        query = self.db.query(SmarshAlert)
        
        if enabled_only:
            query = query.filter(SmarshAlert.enabled == True)
        
        if alert_type:
            query = query.filter(SmarshAlert.alert_type == alert_type)
        
        total = query.count()
        alerts = query.order_by(SmarshAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update(self, alert_id: str, data: SmarshAlertUpdate) -> Optional[SmarshAlert]:
        """Update an alert."""
        alert = self.get(alert_id)
        if not alert:
            return None
        
        update_dict = data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            if value is not None:
                if hasattr(value, 'model_dump'):
                    value = value.model_dump()
                setattr(alert, field, value)
        
        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        
        return alert
    
    def delete(self, alert_id: str) -> bool:
        """Delete an alert."""
        alert = self.get(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    # ============ Metric Computation ============
    
    def _compute_metric(
        self,
        metric_config: Dict[str, Any],
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Compute the metric value for a given time window.
        Returns: (metric_value, top_contributors)
        """
        metric_type = metric_config.get("metric_type", "email_volume")
        
        # Base query
        if metric_type == "email_volume":
            return self._compute_email_volume(filters, start_time, end_time)
        
        elif metric_type == "unique_senders":
            return self._compute_unique_senders(filters, start_time, end_time)
        
        elif metric_type == "entity_mentions":
            entity_type = metric_config.get("entity_type", "ALL")
            entity_value = metric_config.get("entity_value")
            return self._compute_entity_mentions(entity_type, entity_value, filters, start_time, end_time)
        
        elif metric_type == "keyword_matches":
            keywords = metric_config.get("keywords", [])
            return self._compute_keyword_matches(keywords, filters, start_time, end_time)
        
        return 0, []
    
    def _compute_email_volume(
        self,
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Count emails in time window."""
        query = self.db.query(func.count(Email.id)).filter(
            Email.date >= start_time,
            Email.date < end_time
        )
        
        # Apply filters
        query = self._apply_email_filters(query, filters)
        
        count = query.scalar() or 0
        
        # Get top senders as contributors
        top_senders = self.db.query(
            Email.sender,
            func.count(Email.id).label('count')
        ).filter(
            Email.date >= start_time,
            Email.date < end_time
        ).group_by(Email.sender).order_by(func.count(Email.id).desc()).limit(5).all()
        
        contributors = [{"sender": s, "count": c} for s, c in top_senders]
        
        return float(count), contributors
    
    def _compute_unique_senders(
        self,
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Count unique senders in time window."""
        query = self.db.query(func.count(distinct(Email.sender))).filter(
            Email.date >= start_time,
            Email.date < end_time
        )
        
        query = self._apply_email_filters(query, filters)
        count = query.scalar() or 0
        
        # Get top senders
        top_senders = self.db.query(
            Email.sender,
            func.count(Email.id).label('count')
        ).filter(
            Email.date >= start_time,
            Email.date < end_time
        ).group_by(Email.sender).order_by(func.count(Email.id).desc()).limit(5).all()
        
        contributors = [{"sender": s, "count": c} for s, c in top_senders]
        
        return float(count), contributors
    
    def _compute_entity_mentions(
        self,
        entity_type: str,
        entity_value: Optional[str],
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Count entity mentions in time window."""
        query = self.db.query(func.count(Entity.id)).join(Email).filter(
            Email.date >= start_time,
            Email.date < end_time
        )
        
        if entity_type and entity_type != "ALL":
            query = query.filter(Entity.type == entity_type)
        
        if entity_value:
            query = query.filter(Entity.text.ilike(f"%{entity_value}%"))
        
        count = query.scalar() or 0
        
        # Get top entities
        top_query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label('count')
        ).join(Email).filter(
            Email.date >= start_time,
            Email.date < end_time
        )
        
        if entity_type and entity_type != "ALL":
            top_query = top_query.filter(Entity.type == entity_type)
        
        top_entities = top_query.group_by(Entity.text, Entity.type)\
            .order_by(func.count(Entity.id).desc()).limit(5).all()
        
        contributors = [{"entity": t, "type": tp, "count": c} for t, tp, c in top_entities]
        
        return float(count), contributors
    
    def _compute_keyword_matches(
        self,
        keywords: List[str],
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Count keyword matches in email body/subject."""
        if not keywords:
            return 0, []
        
        # Count emails containing any keyword
        from sqlalchemy import or_
        
        conditions = []
        for kw in keywords:
            conditions.append(Email.body.ilike(f"%{kw}%"))
            conditions.append(Email.subject.ilike(f"%{kw}%"))
        
        query = self.db.query(func.count(Email.id)).filter(
            Email.date >= start_time,
            Email.date < end_time,
            or_(*conditions)
        )
        
        count = query.scalar() or 0
        
        contributors = [{"keyword": kw, "searched": True} for kw in keywords[:5]]
        
        return float(count), contributors
    
    def _apply_email_filters(self, query, filters: Optional[Dict[str, Any]]):
        """Apply dimension filters to query."""
        if not filters:
            return query
        
        if filters.get("sender_domains"):
            from sqlalchemy import or_
            domain_conditions = [
                Email.sender.ilike(f"%@{domain}")
                for domain in filters["sender_domains"]
            ]
            query = query.filter(or_(*domain_conditions))
        
        return query
    
    # ============ Time Series Computation ============
    
    def _get_time_series(
        self,
        metric_config: Dict[str, Any],
        filters: Optional[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get time series data for the metric."""
        series = []
        current = start_time
        
        while current < end_time:
            next_time = current + timedelta(minutes=interval_minutes)
            value, _ = self._compute_metric(metric_config, filters, current, next_time)
            series.append({
                "timestamp": current.isoformat(),
                "value": value
            })
            current = next_time
        
        return series
    
    # ============ Anomaly Detection ============
    
    def _compute_baseline_stats(
        self,
        values: List[float]
    ) -> Tuple[float, float]:
        """Compute mean and standard deviation."""
        if not values:
            return 0, 0
        
        n = len(values)
        mean = sum(values) / n
        
        if n < 2:
            return mean, 0
        
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
        
        return mean, std
    
    def _compute_zscore(self, value: float, mean: float, std: float) -> float:
        """Compute Z-score."""
        if std == 0:
            return 0 if value == mean else float('inf') if value > mean else float('-inf')
        return (value - mean) / std
    
    def _compute_ewma(self, values: List[float], span: int = 7) -> float:
        """Compute Exponentially Weighted Moving Average."""
        if not values:
            return 0
        
        alpha = 2 / (span + 1)
        ewma = values[0]
        
        for value in values[1:]:
            ewma = alpha * value + (1 - alpha) * ewma
        
        return ewma
    
    # ============ Alert Evaluation ============
    
    def evaluate(self, alert: SmarshAlert) -> Dict[str, Any]:
        """
        Evaluate an alert and determine if it should trigger.
        
        Returns detailed evaluation result.
        
        Uses latest email date as reference point to support historical data.
        """
        # Use latest email date instead of current time for historical data support
        now = self.get_latest_email_date()
        window_minutes = alert.get_window_minutes()
        
        # Current window
        current_start = now - timedelta(minutes=window_minutes)
        current_end = now
        
        # Get metric config
        metric_config = alert.metric or {}
        filters = alert.filters
        
        # Compute current value
        current_value, top_contributors = self._compute_metric(
            metric_config, filters, current_start, current_end
        )
        
        # Get time series for visualization
        time_series = self._get_time_series(
            metric_config, filters,
            now - timedelta(days=7),  # Last 7 days for chart
            now,
            interval_minutes=60 if window_minutes <= 1440 else 1440
        )
        
        result = {
            "alert_id": alert.id,
            "alert_name": alert.name,
            "alert_type": alert.alert_type,
            "triggered": False,
            "trigger_reason": None,
            "current_value": current_value,
            "baseline_value": 0,
            "zscore": None,
            "percentage_change": None,
            "time_series": time_series,
            "in_cooldown": False,
            "cooldown_remaining_minutes": 0,
            "alerts_today": alert.alerts_today or 0,
            "top_contributors": top_contributors
        }
        
        # Check cooldown
        cooldown_config = alert.cooldown or {}
        if cooldown_config.get("enabled", True):
            # Reset daily count if needed
            alert.reset_daily_count_if_needed()
            
            # Check max alerts per day
            max_per_day = cooldown_config.get("max_alerts_per_day", 10)
            if alert.alerts_today >= max_per_day:
                result["in_cooldown"] = True
                result["trigger_reason"] = f"Max alerts per day reached ({max_per_day})"
                self._update_alert_state(alert, current_value, 0, None)
                return result
            
            # Check cooldown period
            cooldown_minutes = cooldown_config.get("cooldown_minutes", 60)
            if alert.last_triggered_at:
                cooldown_end = alert.last_triggered_at + timedelta(minutes=cooldown_minutes)
                if now < cooldown_end:
                    remaining = int((cooldown_end - now).total_seconds() / 60)
                    result["in_cooldown"] = True
                    result["cooldown_remaining_minutes"] = remaining
                    result["trigger_reason"] = f"In cooldown for {remaining} more minutes"
                    self._update_alert_state(alert, current_value, 0, None)
                    return result
        
        # Evaluate based on alert type
        if alert.alert_type == "static":
            result = self._evaluate_static(alert, current_value, result)
        else:  # smart
            result = self._evaluate_smart(alert, current_value, metric_config, filters, result)
        
        # Handle alert longevity (consecutive anomalies)
        if result["triggered"]:
            consecutive_required = cooldown_config.get("consecutive_anomalies", 1)
            alert.consecutive_anomaly_count = (alert.consecutive_anomaly_count or 0) + 1
            
            if alert.consecutive_anomaly_count < consecutive_required:
                result["triggered"] = False
                result["trigger_reason"] = (
                    f"Anomaly detected ({alert.consecutive_anomaly_count}/{consecutive_required} consecutive required)"
                )
        else:
            alert.consecutive_anomaly_count = 0
        
        # Record trigger if needed
        if result["triggered"]:
            self._record_trigger(alert, result)
        
        # Update alert state
        self._update_alert_state(
            alert, 
            current_value, 
            result.get("baseline_value", 0),
            result.get("zscore")
        )
        
        result["alerts_today"] = alert.alerts_today
        
        return result
    
    def _evaluate_static(
        self,
        alert: SmarshAlert,
        current_value: float,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate static threshold alert."""
        threshold_config = alert.threshold or {}
        operator = threshold_config.get("operator", "greater_than")
        threshold_value = threshold_config.get("value", 100)
        
        result["baseline_value"] = threshold_value
        
        triggered = False
        if operator == "greater_than":
            triggered = current_value > threshold_value
        elif operator == "less_than":
            triggered = current_value < threshold_value
        elif operator == "equals":
            triggered = current_value == threshold_value
        elif operator == "not_equals":
            triggered = current_value != threshold_value
        
        if triggered:
            result["triggered"] = True
            result["trigger_reason"] = (
                f"Metric value {current_value:.0f} is {operator.replace('_', ' ')} threshold {threshold_value:.0f}"
            )
        
        return result
    
    def _evaluate_smart(
        self,
        alert: SmarshAlert,
        current_value: float,
        metric_config: Dict[str, Any],
        filters: Optional[Dict[str, Any]],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate smart/anomaly alert using Z-score or other algorithms."""
        anomaly_config = alert.anomaly or {}
        algorithm = anomaly_config.get("algorithm", "zscore")
        time_window = alert.time_window or {}
        baseline_days = time_window.get("baseline_days", 7)
        window_minutes = alert.get_window_minutes()
        
        # Use latest email date instead of current time for historical data support
        now = self.get_latest_email_date()
        
        # Compute baseline values (same window for each day in baseline period)
        baseline_values = []
        for day_offset in range(1, baseline_days + 1):
            day_start = now - timedelta(days=day_offset, minutes=window_minutes)
            day_end = now - timedelta(days=day_offset)
            value, _ = self._compute_metric(metric_config, filters, day_start, day_end)
            baseline_values.append(value)
        
        min_baseline = anomaly_config.get("min_baseline_count", 10)
        
        if len(baseline_values) < 2:
            result["trigger_reason"] = "Insufficient baseline data"
            return result
        
        mean, std = self._compute_baseline_stats(baseline_values)
        result["baseline_value"] = mean
        
        if algorithm == "zscore":
            zscore_threshold = anomaly_config.get("zscore_threshold", 2.5)
            zscore = self._compute_zscore(current_value, mean, std)
            result["zscore"] = round(zscore, 2)
            
            if abs(zscore) >= zscore_threshold:
                direction = "above" if zscore > 0 else "below"
                result["triggered"] = True
                result["trigger_reason"] = (
                    f"Anomaly detected: Z-score {zscore:.2f} ({direction} baseline). "
                    f"Current: {current_value:.0f}, Expected: {mean:.0f} ± {std:.0f}"
                )
        
        elif algorithm == "ewma":
            ewma_span = anomaly_config.get("ewma_span", 7)
            ewma_value = self._compute_ewma(baseline_values, ewma_span)
            zscore_threshold = anomaly_config.get("zscore_threshold", 2.5)
            
            # Use EWMA as baseline and compute deviation
            deviation = abs(current_value - ewma_value)
            relative_deviation = deviation / ewma_value if ewma_value > 0 else 0
            
            result["baseline_value"] = ewma_value
            
            if relative_deviation > (zscore_threshold / 10):  # Scale threshold
                result["triggered"] = True
                result["trigger_reason"] = (
                    f"EWMA anomaly: Current {current_value:.0f} vs EWMA {ewma_value:.0f} "
                    f"(deviation: {relative_deviation*100:.1f}%)"
                )
        
        elif algorithm == "percentage_change":
            pct_threshold = anomaly_config.get("percentage_threshold", 50)
            
            if mean > 0:
                pct_change = ((current_value - mean) / mean) * 100
                result["percentage_change"] = round(pct_change, 1)
                
                if abs(pct_change) >= pct_threshold:
                    direction = "increase" if pct_change > 0 else "decrease"
                    result["triggered"] = True
                    result["trigger_reason"] = (
                        f"{abs(pct_change):.1f}% {direction} detected. "
                        f"Current: {current_value:.0f}, Baseline avg: {mean:.0f}"
                    )
        
        return result
    
    def _update_alert_state(
        self,
        alert: SmarshAlert,
        current_value: float,
        baseline_value: float,
        zscore: Optional[float]
    ):
        """Update alert tracking state."""
        alert.last_checked_at = datetime.utcnow()
        alert.last_value = current_value
        alert.last_baseline = baseline_value
        alert.last_zscore = zscore
        self.db.commit()
    
    def _record_trigger(self, alert: SmarshAlert, result: Dict[str, Any]):
        """Record alert trigger in history."""
        history = SmarshAlertHistory(
            alert_id=alert.id,
            triggered_at=datetime.utcnow(),
            metric_value=result.get("current_value", 0),
            baseline_value=result.get("baseline_value", 0),
            zscore=result.get("zscore"),
            percentage_change=result.get("percentage_change"),
            trigger_reason=result.get("trigger_reason"),
            top_contributors=result.get("top_contributors", []),
            time_series_snapshot=result.get("time_series", [])[-24:]  # Last 24 points
        )
        
        self.db.add(history)
        
        # Update alert counters
        alert.last_triggered_at = datetime.utcnow()
        alert.trigger_count = (alert.trigger_count or 0) + 1
        alert.alerts_today = (alert.alerts_today or 0) + 1
        
        self.db.commit()
        self.db.refresh(history)
        
        return history
    
    def evaluate_all(self) -> List[Dict[str, Any]]:
        """Evaluate all enabled alerts."""
        alerts, _ = self.list(enabled_only=True)
        results = []
        
        for alert in alerts:
            result = self.evaluate(alert)
            if result["triggered"]:
                results.append(result)
        
        return results
    
    # ============ History ============
    
    def get_history(
        self,
        alert_id: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[SmarshAlertHistory], int]:
        """Get alert trigger history."""
        query = self.db.query(SmarshAlertHistory)
        
        if alert_id:
            query = query.filter(SmarshAlertHistory.alert_id == alert_id)
        
        total = query.count()
        history = query.order_by(SmarshAlertHistory.triggered_at.desc()).limit(limit).all()
        
        return history, total
    
    def get_triggered_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recently triggered alerts."""
        history = self.db.query(SmarshAlertHistory)\
            .order_by(SmarshAlertHistory.triggered_at.desc())\
            .limit(limit)\
            .all()
        
        results = []
        for h in history:
            alert = self.get(h.alert_id)
            results.append({
                "history_id": h.id,
                "alert_id": h.alert_id,
                "alert_name": alert.name if alert else "Unknown",
                "severity": alert.severity if alert else "medium",
                "triggered_at": h.triggered_at.isoformat(),
                "metric_value": h.metric_value,
                "baseline_value": h.baseline_value,
                "zscore": h.zscore,
                "percentage_change": h.percentage_change,
                "trigger_reason": h.trigger_reason,
                "top_contributors": h.top_contributors
            })
        
        return results
    
    # ============ Dashboard Helpers ============
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get overall alert statistics."""
        total_alerts = self.db.query(SmarshAlert).count()
        enabled_alerts = self.db.query(SmarshAlert).filter(SmarshAlert.enabled == True).count()
        
        # Triggered in last 24h
        yesterday = datetime.utcnow() - timedelta(days=1)
        triggered_24h = self.db.query(SmarshAlertHistory)\
            .filter(SmarshAlertHistory.triggered_at >= yesterday).count()
        
        # By severity
        severity_counts = {}
        for severity in ["low", "medium", "high", "critical"]:
            count = self.db.query(SmarshAlert)\
                .filter(SmarshAlert.severity == severity, SmarshAlert.enabled == True).count()
            severity_counts[severity] = count
        
        return {
            "total_alerts": total_alerts,
            "enabled_alerts": enabled_alerts,
            "triggered_last_24h": triggered_24h,
            "by_severity": severity_counts
        }
