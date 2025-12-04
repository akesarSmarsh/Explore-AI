"""Alert scheduler service for periodic alert evaluation and notifications."""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from threading import Thread
import time

from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.models.unified_alert import UnifiedAlert
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.email_notification_service import email_notification_service

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Scheduler for periodic alert evaluation and notifications."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self._last_check: Dict[int, datetime] = {}  # Track last check per alert
    
    def start(self):
        """Start the scheduler."""
        if not settings.enable_scheduler:
            logger.info("Alert scheduler is disabled in settings")
            return
        
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # Add job to check alerts periodically
        self.scheduler.add_job(
            self._check_all_alerts,
            IntervalTrigger(minutes=settings.alert_check_interval_minutes),
            id='check_alerts',
            name='Check all enabled alerts',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Alert scheduler started - checking every {settings.alert_check_interval_minutes} minutes")
    
    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Alert scheduler stopped")
    
    def trigger_now(self):
        """Trigger an immediate check of all alerts."""
        logger.info("Triggering immediate alert check")
        Thread(target=self._check_all_alerts).start()
    
    def _check_all_alerts(self):
        """Check all enabled alerts and send notifications for triggered ones."""
        logger.info("Starting scheduled alert check...")
        
        db = SessionLocal()
        try:
            # Get all enabled alerts
            alerts = db.query(UnifiedAlert).filter(UnifiedAlert.enabled == True).all()
            logger.info(f"Found {len(alerts)} enabled alerts to check")
            
            triggered_count = 0
            for alert in alerts:
                try:
                    triggered = self._evaluate_alert(db, alert)
                    if triggered:
                        triggered_count += 1
                except Exception as e:
                    logger.error(f"Error evaluating alert {alert.id} ({alert.name}): {e}")
            
            logger.info(f"Alert check complete. {triggered_count}/{len(alerts)} alerts triggered.")
            
        except Exception as e:
            logger.error(f"Error in scheduled alert check: {e}")
        finally:
            db.close()
    
    def _evaluate_alert(self, db: Session, alert: UnifiedAlert) -> bool:
        """
        Evaluate a single alert and send notification if triggered.
        
        Returns True if alert was triggered.
        """
        service = AnomalyDetectionService(db)
        
        # Determine time window based on alert settings
        window_hours = alert.window_hours or 24
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=window_hours)
        
        # Evaluate based on alert category
        if alert.category == 'data_quality':
            result = service.evaluate_data_quality_alert(
                algorithm=alert.detection_algorithm or 'dbscan',
                window_hours=window_hours,
                baseline_days=alert.baseline_days or 30,
                dbscan_eps=alert.dbscan_eps or 0.5,
                dbscan_min_samples=alert.dbscan_min_samples or 3,
                kmeans_clusters=alert.kmeans_clusters or 3
            )
        elif alert.category == 'entity_type':
            result = service.evaluate_entity_alert(
                entity_type=alert.entity_type or 'PERSON',
                entity_value=alert.entity_value,
                algorithm=alert.detection_algorithm or 'dbscan',
                window_hours=window_hours,
                baseline_days=alert.baseline_days or 30,
                dbscan_eps=alert.dbscan_eps or 0.5,
                dbscan_min_samples=alert.dbscan_min_samples or 3,
                kmeans_clusters=alert.kmeans_clusters or 3
            )
        elif alert.category == 'smart_ai':
            # Smart AI uses the description for pattern matching
            result = self._evaluate_smart_ai_alert(db, alert, start_date, end_date)
        else:
            logger.warning(f"Unknown alert category: {alert.category}")
            return False
        
        # Check if anomalies were detected
        anomalies = result.get('anomalies', [])
        if not anomalies:
            return False
        
        # Check if we should send notification (avoid spamming)
        last_check = self._last_check.get(alert.id)
        if last_check:
            # Don't notify if we already notified in the last hour
            if datetime.now() - last_check < timedelta(hours=1):
                logger.debug(f"Skipping notification for alert {alert.id} - notified recently")
                return True
        
        # Send notification
        alert_dict = {
            'id': alert.id,
            'name': alert.name,
            'description': alert.description,
            'category': alert.category,
            'severity': alert.severity,
            'entity_type': alert.entity_type,
            'entity_value': alert.entity_value
        }
        
        success = email_notification_service.send_alert_notification(alert_dict, anomalies)
        
        if success:
            self._last_check[alert.id] = datetime.now()
            
            # Update alert's last triggered time
            alert.last_triggered = datetime.now()
            alert.trigger_count = (alert.trigger_count or 0) + 1
            db.commit()
            
            logger.info(f"Alert triggered and notification sent: {alert.name}")
        
        return True
    
    def _evaluate_smart_ai_alert(
        self, 
        db: Session, 
        alert: UnifiedAlert,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Evaluate a Smart AI alert using semantic search."""
        from app.services.search_service import SearchService
        from app.schemas.search import SemanticSearchRequest, SearchFilters
        
        if not alert.description:
            return {'anomalies': []}
        
        try:
            search_service = SearchService(db)
            
            # Use the description as search query
            request = SemanticSearchRequest(
                query=alert.description,
                limit=50,
                filters=SearchFilters(
                    date_from=start_date,
                    date_to=end_date
                )
            )
            
            results = search_service.semantic_search(request)
            
            # Filter by similarity threshold
            threshold = alert.similarity_threshold or 0.7
            matching_emails = [r for r in results if r.relevance_score >= threshold]
            
            if not matching_emails:
                return {'anomalies': []}
            
            # If we found matching emails above threshold, consider it triggered
            # Group by hour for anomaly reporting
            hourly_counts: Dict[str, int] = {}
            for email in matching_emails:
                if email.date:
                    hour_key = email.date.strftime('%Y-%m-%d %H:00')
                    hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            
            anomalies = [
                {
                    'timestamp': ts,
                    'count': count,
                    'anomaly_type': 'semantic_match',
                    'is_anomaly': True
                }
                for ts, count in sorted(hourly_counts.items(), reverse=True)
            ]
            
            return {'anomalies': anomalies, 'total_matches': len(matching_emails)}
            
        except Exception as e:
            logger.error(f"Error in Smart AI alert evaluation: {e}")
            return {'anomalies': []}


# Global scheduler instance
alert_scheduler = AlertScheduler()
