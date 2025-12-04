"""Scheduler Service for background alert checking."""
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
import threading
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal
from app.models import SmartAlert
from app.models.unified_alert import DataQualityAlert, EntityTypeAlert, SmartAIAlert
from app.services.smart_alert_service import SmartAlertService
from app.services.notification_service import NotificationService
from app.services.email_notification_service import email_notification_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling background alert checks."""
    
    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[BackgroundScheduler] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the scheduler."""
        if not self._initialized:
            self._scheduler = BackgroundScheduler()
            self._initialized = True
    
    def start(self):
        """Start the scheduler."""
        if not self._scheduler.running:
            # Add default jobs
            self._add_default_jobs()
            self._scheduler.start()
            logger.info("Scheduler started")
            
            # Run initial full historical scan on startup
            print("[SCHEDULER] Running initial historical alert scan on startup...")
            import threading
            threading.Thread(target=self._run_initial_historical_scan, daemon=True).start()
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
    
    def _add_default_jobs(self):
        """Add default scheduled jobs."""
        # Check unified alerts based on config interval
        self._scheduler.add_job(
            self._check_unified_alerts,
            trigger=IntervalTrigger(minutes=settings.alert_check_interval_minutes),
            id="unified_alert_check",
            replace_existing=True
        )
        
        # Check hourly alerts every hour
        self._scheduler.add_job(
            self._check_hourly_alerts,
            trigger=IntervalTrigger(hours=1),
            id="hourly_alert_check",
            replace_existing=True
        )
        
        # Check daily alerts every day at 9 AM
        self._scheduler.add_job(
            self._check_daily_alerts,
            trigger=CronTrigger(hour=9, minute=0),
            id="daily_alert_check",
            replace_existing=True
        )
        
        # Check weekly alerts every Monday at 9 AM
        self._scheduler.add_job(
            self._check_weekly_alerts,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_alert_check",
            replace_existing=True
        )
        
        logger.info(f"Default scheduled jobs added. Unified alerts check every {settings.alert_check_interval_minutes} minutes")
    
    def _check_unified_alerts(self):
        """Check all enabled unified alerts and send email notifications."""
        print("[SCHEDULER] ========== STARTING ALERT CHECK ==========")
        logger.info("Running unified alert check...")
        
        db = SessionLocal()
        try:
            from app.services.anomaly_detection_service import AnomalyDetectionService
            
            triggered_count = 0
            total_count = 0
            
            # Check Data Quality alerts
            dq_alerts = db.query(DataQualityAlert).filter(DataQualityAlert.enabled == True).all()
            print(f"[SCHEDULER] Found {len(dq_alerts)} enabled Data Quality alerts")
            total_count += len(dq_alerts)
            for alert in dq_alerts:
                try:
                    triggered = self._evaluate_data_quality_alert(db, alert)
                    if triggered:
                        triggered_count += 1
                except Exception as e:
                    print(f"[SCHEDULER] ERROR in data quality alert: {e}")
                    logger.error(f"Error evaluating data quality alert {alert.id}: {e}")
            
            # Check Entity Type alerts
            et_alerts = db.query(EntityTypeAlert).filter(EntityTypeAlert.enabled == True).all()
            print(f"[SCHEDULER] Found {len(et_alerts)} enabled Entity Type alerts")
            total_count += len(et_alerts)
            for alert in et_alerts:
                try:
                    triggered = self._evaluate_entity_type_alert(db, alert)
                    if triggered:
                        triggered_count += 1
                except Exception as e:
                    print(f"[SCHEDULER] ERROR in entity type alert: {e}")
                    logger.error(f"Error evaluating entity type alert {alert.id}: {e}")
            
            # Check Smart AI alerts
            sa_alerts = db.query(SmartAIAlert).filter(SmartAIAlert.enabled == True).all()
            print(f"[SCHEDULER] Found {len(sa_alerts)} enabled Smart AI alerts")
            total_count += len(sa_alerts)
            for alert in sa_alerts:
                print(f"[SCHEDULER] Evaluating Smart AI alert: {alert.name}")
                try:
                    triggered = self._evaluate_smart_ai_alert_notification(db, alert)
                    print(f"[SCHEDULER] Smart AI alert '{alert.name}' triggered: {triggered}")
                    if triggered:
                        triggered_count += 1
                except Exception as e:
                    print(f"[SCHEDULER] ERROR in smart AI alert: {e}")
                    logger.error(f"Error evaluating smart AI alert {alert.id}: {e}")
            
            print(f"[SCHEDULER] ========== COMPLETE: {triggered_count}/{total_count} triggered ==========")
            logger.info(f"Unified alert check complete. {triggered_count}/{total_count} alerts triggered.")
            
        except Exception as e:
            logger.error(f"Error in unified alert check: {e}")
        finally:
            db.close()
    
    def _evaluate_data_quality_alert(self, db, alert: DataQualityAlert) -> bool:
        """Evaluate a data quality alert and send notification if triggered."""
        from app.services.anomaly_detection_service import AnomalyDetectionService
        
        service = AnomalyDetectionService(db)
        result = service.evaluate_data_quality_alert(
            algorithm='dbscan',
            window_hours=24,
            baseline_days=30
        )
        
        anomalies = result.get('anomalies', [])
        if not anomalies:
            return False
        
        # Check cooldown
        if alert.last_triggered_at:
            if datetime.utcnow() - alert.last_triggered_at < timedelta(hours=1):
                return True
        
        alert_dict = {
            'id': alert.id,
            'name': alert.name,
            'description': alert.description or f"Data quality alert: {alert.quality_type}",
            'category': 'data_quality',
            'severity': alert.severity
        }
        
        success = email_notification_service.send_alert_notification(alert_dict, anomalies)
        if success:
            alert.last_triggered_at = datetime.utcnow()
            alert.trigger_count = (alert.trigger_count or 0) + 1
            db.commit()
            logger.info(f"Data quality alert triggered: {alert.name}")
        
        return True
    
    def _evaluate_entity_type_alert(self, db, alert: EntityTypeAlert) -> bool:
        """Evaluate an entity type alert and send notification if triggered."""
        from app.services.anomaly_detection_service import AnomalyDetectionService
        
        service = AnomalyDetectionService(db)
        result = service.evaluate_entity_alert(
            entity_type=alert.entity_type or 'PERSON',
            entity_value=alert.entity_value,
            algorithm=alert.detection_algorithm or 'dbscan',
            window_hours=alert.window_hours or 24,
            baseline_days=alert.baseline_days or 7,
            dbscan_eps=alert.dbscan_eps or 0.5,
            dbscan_min_samples=alert.dbscan_min_samples or 3,
            kmeans_clusters=alert.kmeans_clusters or 3
        )
        
        anomalies = result.get('anomalies', [])
        if not anomalies:
            return False
        
        # Check cooldown
        if alert.last_triggered_at:
            if datetime.utcnow() - alert.last_triggered_at < timedelta(hours=1):
                return True
        
        alert_dict = {
            'id': alert.id,
            'name': alert.name,
            'description': alert.description or f"Entity type alert: {alert.entity_type}",
            'category': 'entity_type',
            'severity': alert.severity,
            'entity_type': alert.entity_type,
            'entity_value': alert.entity_value
        }
        
        success = email_notification_service.send_alert_notification(alert_dict, anomalies)
        if success:
            alert.last_triggered_at = datetime.utcnow()
            alert.trigger_count = (alert.trigger_count or 0) + 1
            db.commit()
            logger.info(f"Entity type alert triggered: {alert.name}")
        
        return True
    
    def _evaluate_smart_ai_alert_notification(self, db, alert: SmartAIAlert) -> bool:
        """Evaluate a Smart AI alert and send notification if triggered."""
        window_hours = 24  # Default window
        result = self._evaluate_smart_ai_alert_internal(db, alert, window_hours)
        
        anomalies = result.get('anomalies', [])
        if not anomalies:
            return False
        
        # Check cooldown
        if alert.last_triggered_at:
            if datetime.utcnow() - alert.last_triggered_at < timedelta(hours=1):
                return True
        
        alert_dict = {
            'id': alert.id,
            'name': alert.name,
            'description': alert.description,
            'category': 'smart_ai',
            'severity': alert.severity
        }
        
        success = email_notification_service.send_alert_notification(alert_dict, anomalies)
        if success:
            alert.last_triggered_at = datetime.utcnow()
            alert.trigger_count = (alert.trigger_count or 0) + 1
            
            # Save to history
            from app.models.unified_alert import SmartAIAlertHistory
            history = SmartAIAlertHistory(
                alert_id=alert.id,
                triggered_at=datetime.utcnow(),
                anomaly_detected=True,
                anomaly_details={'anomalies': anomalies},
                trigger_reason=f"Found {len(anomalies)} anomalies matching '{alert.description}'"
            )
            db.add(history)
            db.commit()
            logger.info(f"Smart AI alert triggered: {alert.name}")
            print(f"[SCHEDULER] Alert history saved for: {alert.name}")
        
        return True
    
    def _evaluate_smart_ai_alert_internal(self, db, alert: SmartAIAlert, window_hours: int) -> Dict[str, Any]:
        """Evaluate a Smart AI unified alert using semantic search."""
        if not alert.description:
            return {'anomalies': []}
        
        try:
            from app.services.search_service import SearchService
            from app.schemas.search import SemanticSearchRequest, SearchFilters
            from sqlalchemy import func
            from app.models.email import Email
            
            # Get actual date range from database (for historical data like Enron)
            date_range = db.query(
                func.min(Email.date).label('min_date'),
                func.max(Email.date).label('max_date')
            ).filter(Email.date.isnot(None)).first()
            
            if date_range.max_date:
                end_date = date_range.max_date
                start_date = end_date - timedelta(hours=window_hours)
                print(f"[SMART AI EVAL] Using data date range: {start_date} to {end_date}")
            else:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(hours=window_hours)
            
            search_service = SearchService(db)
            # Search without date filter to find all matching emails
            request = SemanticSearchRequest(
                query=alert.description,
                limit=100
            )
            
            results = search_service.semantic_search(request)
            threshold = alert.similarity_threshold or 0.3  # Lower threshold
            matching = [r for r in results if r.relevance_score >= threshold]
            
            print(f"[SMART AI EVAL] Found {len(matching)} emails matching '{alert.description}' above threshold {threshold}")
            
            if not matching:
                return {'anomalies': []}
            
            # Group by day (since data spans years)
            daily: Dict[str, int] = {}
            for email in matching:
                if email.date:
                    key = email.date.strftime('%Y-%m-%d')
                    daily[key] = daily.get(key, 0) + 1
            
            anomalies = [
                {'timestamp': ts, 'count': count, 'anomaly_type': 'semantic_match', 'is_anomaly': True}
                for ts, count in sorted(daily.items(), reverse=True)[:10]  # Top 10 days
            ]
            
            print(f"[SMART AI EVAL] Generated {len(anomalies)} anomaly entries")
            return {'anomalies': anomalies}
            
        except Exception as e:
            logger.error(f"Error in Smart AI alert evaluation: {e}")
            print(f"[SMART AI EVAL] ERROR: {e}")
            return {'anomalies': []}
    
    def trigger_unified_alerts_now(self):
        """Trigger an immediate check of all unified alerts."""
        logger.info("Triggering immediate unified alert check")
        threading.Thread(target=self._check_unified_alerts).start()
    
    def _run_initial_historical_scan(self):
        """
        Run a full historical scan on startup to detect all past anomalies.
        Sends email notifications for any anomalies found in historical data.
        Covers ALL alert types: Data Quality, Entity Type, and Smart AI.
        """
        import time
        time.sleep(2)  # Wait for server to fully start
        
        print("[STARTUP SCAN] ========== STARTING FULL HISTORICAL SCAN ==========")
        logger.info("Running initial historical alert scan on startup")
        
        db = SessionLocal()
        try:
            from app.services.anomaly_detection_service import AnomalyDetectionService
            from app.models.unified_alert import (
                SmartAIAlertHistory, EntityTypeAlertHistory, DataQualityAlertHistory
            )
            
            total_anomalies = 0
            emails_sent = 0
            
            # ========== DATA QUALITY ALERTS ==========
            dq_alerts = db.query(DataQualityAlert).filter(DataQualityAlert.enabled == True).all()
            print(f"[STARTUP SCAN] Found {len(dq_alerts)} enabled Data Quality alerts")
            
            for alert in dq_alerts:
                print(f"[STARTUP SCAN] Processing Data Quality: {alert.name}")
                result = self._evaluate_data_quality_full_history(db, alert)
                anomalies = result.get('anomalies', [])
                
                if anomalies:
                    total_anomalies += len(anomalies)
                    alert_dict = {
                        'id': alert.id,
                        'name': alert.name,
                        'description': alert.description or f"Data quality: {alert.quality_type}",
                        'category': 'data_quality',
                        'severity': alert.severity
                    }
                    
                    success = email_notification_service.send_alert_notification(alert_dict, anomalies)
                    if success:
                        emails_sent += 1
                        alert.last_triggered_at = datetime.utcnow()
                        alert.trigger_count = (alert.trigger_count or 0) + 1
                        
                        history = DataQualityAlertHistory(
                            alert_id=alert.id,
                            triggered_at=datetime.utcnow(),
                            is_anomaly=True,
                            trigger_reason=f"Startup scan: Found {len(anomalies)} historical anomalies"
                        )
                        db.add(history)
                        db.commit()
                        print(f"[STARTUP SCAN] Email sent for Data Quality: {alert.name}")
            
            # ========== ENTITY TYPE ALERTS ==========
            et_alerts = db.query(EntityTypeAlert).filter(EntityTypeAlert.enabled == True).all()
            print(f"[STARTUP SCAN] Found {len(et_alerts)} enabled Entity Type alerts")
            
            for alert in et_alerts:
                print(f"[STARTUP SCAN] Processing Entity Type: {alert.name}")
                result = self._evaluate_entity_type_full_history(db, alert)
                anomalies = result.get('anomalies', [])
                
                if anomalies:
                    total_anomalies += len(anomalies)
                    alert_dict = {
                        'id': alert.id,
                        'name': alert.name,
                        'description': alert.description or f"Entity: {alert.entity_type} - {alert.entity_value}",
                        'category': 'entity_type',
                        'severity': alert.severity,
                        'entity_type': alert.entity_type,
                        'entity_value': alert.entity_value
                    }
                    
                    success = email_notification_service.send_alert_notification(alert_dict, anomalies)
                    if success:
                        emails_sent += 1
                        alert.last_triggered_at = datetime.utcnow()
                        alert.trigger_count = (alert.trigger_count or 0) + 1
                        
                        history = EntityTypeAlertHistory(
                            alert_id=alert.id,
                            triggered_at=datetime.utcnow(),
                            is_anomaly=True,
                            trigger_reason=f"Startup scan: Found {len(anomalies)} historical anomalies for {alert.entity_type}"
                        )
                        db.add(history)
                        db.commit()
                        print(f"[STARTUP SCAN] Email sent for Entity Type: {alert.name}")
            
            # ========== SMART AI ALERTS ==========
            sa_alerts = db.query(SmartAIAlert).filter(SmartAIAlert.enabled == True).all()
            print(f"[STARTUP SCAN] Found {len(sa_alerts)} enabled Smart AI alerts")
            
            for alert in sa_alerts:
                print(f"[STARTUP SCAN] Processing Smart AI: {alert.name}")
                result = self._evaluate_smart_ai_alert_full_history(db, alert)
                anomalies = result.get('anomalies', [])
                
                if anomalies:
                    total_anomalies += len(anomalies)
                    alert_dict = {
                        'id': alert.id,
                        'name': alert.name,
                        'description': alert.description,
                        'category': 'smart_ai',
                        'severity': alert.severity
                    }
                    
                    success = email_notification_service.send_alert_notification(alert_dict, anomalies)
                    if success:
                        emails_sent += 1
                        alert.last_triggered_at = datetime.utcnow()
                        alert.trigger_count = (alert.trigger_count or 0) + 1
                        
                        history = SmartAIAlertHistory(
                            alert_id=alert.id,
                            triggered_at=datetime.utcnow(),
                            anomaly_detected=True,
                            anomaly_details={'anomalies': anomalies, 'type': 'startup_historical_scan'},
                            trigger_reason=f"Startup scan: Found {len(anomalies)} historical anomalies matching '{alert.description}'"
                        )
                        db.add(history)
                        db.commit()
                        print(f"[STARTUP SCAN] Email sent for Smart AI: {alert.name}")
            
            print(f"[STARTUP SCAN] ========== COMPLETE ==========")
            print(f"[STARTUP SCAN] Total anomalies found: {total_anomalies}")
            print(f"[STARTUP SCAN] Emails sent: {emails_sent}")
            logger.info(f"Historical scan complete. {total_anomalies} anomalies found, {emails_sent} emails sent.")
            
        except Exception as e:
            logger.error(f"Error in historical scan: {e}")
            print(f"[STARTUP SCAN] ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
    
    def _evaluate_data_quality_full_history(self, db, alert: DataQualityAlert) -> Dict[str, Any]:
        """Evaluate a Data Quality alert against ALL historical data."""
        try:
            from app.services.anomaly_detection_service import AnomalyDetectionService
            from sqlalchemy import func
            from app.models.email import Email
            
            # Get full date range
            date_range = db.query(
                func.min(Email.date).label('min_date'),
                func.max(Email.date).label('max_date')
            ).filter(Email.date.isnot(None)).first()
            
            if not date_range.min_date or not date_range.max_date:
                return {'anomalies': []}
            
            service = AnomalyDetectionService(db)
            result = service.analyze_communication_activity_custom(
                start_date=date_range.min_date,
                end_date=date_range.max_date,
                algorithm=alert.detection_algorithm or 'dbscan'
            )
            
            # Extract anomalies from result
            anomalies = []
            for point in result.get('data', []):
                if point.get('is_anomaly'):
                    anomalies.append({
                        'timestamp': point.get('timestamp'),
                        'count': point.get('email_count'),
                        'anomaly_type': point.get('anomaly_type', 'unknown'),
                        'is_anomaly': True
                    })
            
            print(f"[STARTUP SCAN] Data Quality: Found {len(anomalies)} anomalies")
            return {'anomalies': anomalies}
            
        except Exception as e:
            print(f"[STARTUP SCAN] Data Quality ERROR: {e}")
            return {'anomalies': []}
    
    def _evaluate_entity_type_full_history(self, db, alert: EntityTypeAlert) -> Dict[str, Any]:
        """Evaluate an Entity Type alert against ALL historical data."""
        try:
            from app.services.anomaly_detection_service import AnomalyDetectionService
            from sqlalchemy import func
            from app.models.email import Email
            
            # Get full date range
            date_range = db.query(
                func.min(Email.date).label('min_date'),
                func.max(Email.date).label('max_date')
            ).filter(Email.date.isnot(None)).first()
            
            if not date_range.min_date or not date_range.max_date:
                return {'anomalies': []}
            
            service = AnomalyDetectionService(db)
            result = service.analyze_communication_activity_custom(
                start_date=date_range.min_date,
                end_date=date_range.max_date,
                algorithm=alert.detection_algorithm or 'dbscan',
                entity_type=alert.entity_type,
                entity_value=alert.entity_value
            )
            
            # Extract anomalies from result
            anomalies = []
            for point in result.get('data', []):
                if point.get('is_anomaly'):
                    anomalies.append({
                        'timestamp': point.get('timestamp'),
                        'count': point.get('email_count'),
                        'anomaly_type': point.get('anomaly_type', 'unknown'),
                        'is_anomaly': True,
                        'entity_type': alert.entity_type,
                        'entity_value': alert.entity_value
                    })
            
            print(f"[STARTUP SCAN] Entity Type ({alert.entity_type}): Found {len(anomalies)} anomalies")
            return {'anomalies': anomalies}
            
        except Exception as e:
            print(f"[STARTUP SCAN] Entity Type ERROR: {e}")
            return {'anomalies': []}
    
    def _evaluate_smart_ai_alert_full_history(self, db, alert: SmartAIAlert) -> Dict[str, Any]:
        """Evaluate a Smart AI alert against ALL historical data (no time window)."""
        if not alert.description:
            return {'anomalies': []}
        
        try:
            from app.services.search_service import SearchService
            from app.schemas.search import SemanticSearchRequest
            
            search_service = SearchService(db)
            # Search ALL emails - no date filter (max limit is 100)
            request = SemanticSearchRequest(
                query=alert.description,
                limit=100  # Max allowed by schema
            )
            
            results = search_service.semantic_search(request)
            threshold = alert.similarity_threshold or 0.3
            matching = [r for r in results if r.relevance_score >= threshold]
            
            print(f"[STARTUP SCAN] Found {len(matching)} emails matching '{alert.description}'")
            
            if not matching:
                return {'anomalies': []}
            
            # Group by day
            daily: Dict[str, int] = {}
            for email in matching:
                if email.date:
                    key = email.date.strftime('%Y-%m-%d')
                    daily[key] = daily.get(key, 0) + 1
            
            # Find days with unusually high counts (anomalies)
            if not daily:
                return {'anomalies': []}
            
            counts = list(daily.values())
            avg_count = sum(counts) / len(counts)
            
            # Mark days with count > 2x average as anomalies
            anomalies = []
            for ts, count in sorted(daily.items(), reverse=True):
                is_spike = count > avg_count * 1.5
                anomalies.append({
                    'timestamp': ts,
                    'count': count,
                    'anomaly_type': 'spike' if is_spike else 'normal',
                    'is_anomaly': is_spike
                })
            
            # Only return actual anomalies (spikes)
            anomaly_list = [a for a in anomalies if a['is_anomaly']]
            print(f"[STARTUP SCAN] {len(anomaly_list)} spike anomalies detected (avg: {avg_count:.1f})")
            
            return {'anomalies': anomaly_list if anomaly_list else anomalies[:10]}  # Return top 10 if no spikes
            
        except Exception as e:
            logger.error(f"Error in historical Smart AI alert evaluation: {e}")
            print(f"[STARTUP SCAN] ERROR: {e}")
            return {'anomalies': []}
    
    def _check_hourly_alerts(self):
        """Check alerts scheduled for hourly evaluation."""
        self._run_scheduled_alerts("hourly")
    
    def _check_daily_alerts(self):
        """Check alerts scheduled for daily evaluation."""
        self._run_scheduled_alerts("daily")
    
    def _check_weekly_alerts(self):
        """Check alerts scheduled for weekly evaluation."""
        self._run_scheduled_alerts("weekly")
    
    def _run_scheduled_alerts(self, frequency: str):
        """
        Run scheduled alerts of a specific frequency.
        
        Args:
            frequency: hourly, daily, or weekly
        """
        logger.info(f"Running {frequency} alert check")
        
        db = SessionLocal()
        try:
            # Get enabled alerts with matching schedule
            alerts = db.query(SmartAlert).filter(
                SmartAlert.enabled == True
            ).all()
            
            # Filter by schedule frequency
            scheduled_alerts = []
            for alert in alerts:
                schedule = alert.schedule or {}
                if schedule.get("type") == "scheduled":
                    if schedule.get("frequency") == frequency:
                        scheduled_alerts.append(alert)
            
            if not scheduled_alerts:
                logger.info(f"No {frequency} alerts to check")
                return
            
            # Evaluate each alert
            alert_service = SmartAlertService(db)
            notification_service = NotificationService(db)
            
            for alert in scheduled_alerts:
                try:
                    triggered, matched_data = alert_service.evaluate(alert)
                    
                    if triggered:
                        # Create history record
                        history = alert_service._create_history(alert, matched_data)
                        
                        # Send notification
                        notification_service.send_alert_notification(
                            alert, history, matched_data
                        )
                        
                        # Update alert tracking
                        alert.last_triggered_at = datetime.utcnow()
                        alert.trigger_count += 1
                        
                        logger.info(f"Alert '{alert.name}' triggered")
                    
                    alert.last_checked_at = datetime.utcnow()
                
                except Exception as e:
                    logger.error(f"Error evaluating alert {alert.id}: {e}")
            
            db.commit()
            logger.info(f"Completed {frequency} alert check")
        
        except Exception as e:
            logger.error(f"Error in scheduled alert check: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    def add_custom_job(
        self,
        job_id: str,
        func: Callable,
        trigger_type: str = "interval",
        **trigger_kwargs
    ):
        """
        Add a custom scheduled job.
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            trigger_type: "interval" or "cron"
            **trigger_kwargs: Trigger-specific arguments
        """
        if trigger_type == "interval":
            trigger = IntervalTrigger(**trigger_kwargs)
        elif trigger_type == "cron":
            trigger = CronTrigger(**trigger_kwargs)
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")
        
        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Added custom job: {job_id}")
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.warning(f"Could not remove job {job_id}: {e}")
    
    def get_jobs(self):
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in self._scheduler.get_jobs()
        ]
    
    def run_alert_now(self, alert_id: str) -> dict:
        """
        Run a specific alert immediately.
        
        Args:
            alert_id: The alert ID to run
            
        Returns:
            Result of the alert evaluation
        """
        db = SessionLocal()
        try:
            alert = db.query(SmartAlert).filter(SmartAlert.id == alert_id).first()
            if not alert:
                return {"error": "Alert not found"}
            
            alert_service = SmartAlertService(db)
            notification_service = NotificationService(db)
            
            triggered, matched_data = alert_service.evaluate(alert)
            
            if triggered:
                history = alert_service._create_history(alert, matched_data)
                notification_service.send_alert_notification(
                    alert, history, matched_data
                )
                alert.last_triggered_at = datetime.utcnow()
                alert.trigger_count += 1
            
            alert.last_checked_at = datetime.utcnow()
            db.commit()
            
            return {
                "alert_id": alert_id,
                "triggered": triggered,
                "matched_data": matched_data
            }
        
        finally:
            db.close()


# Global scheduler instance
scheduler_service = SchedulerService()










