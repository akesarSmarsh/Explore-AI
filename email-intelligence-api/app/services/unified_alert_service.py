"""Unified Alert Service - Manages Data Quality, Entity Type, and Smart AI alerts."""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.unified_alert import (
    DataQualityAlert, DataQualityAlertHistory,
    EntityTypeAlert, EntityTypeAlertHistory,
    SmartAIAlert, SmartAIAlertHistory,
    CommunicationActivity
)
from app.models.email import Email
from app.models.entity import Entity
from app.schemas.unified_alert import (
    DataQualityAlertCreate, DataQualityAlertUpdate,
    EntityTypeAlertCreate, EntityTypeAlertUpdate,
    SmartAIAlertCreate, SmartAIAlertUpdate
)
from app.services.anomaly_detection_service import AnomalyDetectionService


class UnifiedAlertService:
    """Service for managing all types of alerts."""
    
    def __init__(self, db: Session):
        self.db = db
        self.anomaly_service = AnomalyDetectionService(db)
    
    # ============ Data Quality Alerts ============
    
    def create_data_quality_alert(self, data: DataQualityAlertCreate) -> DataQualityAlert:
        """Create a new Data Quality alert."""
        alert = DataQualityAlert(
            name=data.name,
            description=data.description,
            quality_type=data.quality_type,
            file_format=data.file_format,
            file_size_min=data.file_size_min,
            file_size_max=data.file_size_max,
            severity=data.severity,
            enabled=data.enabled
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get_data_quality_alert(self, alert_id: str) -> Optional[DataQualityAlert]:
        """Get a Data Quality alert by ID."""
        return self.db.query(DataQualityAlert).filter(DataQualityAlert.id == alert_id).first()
    
    def get_data_quality_alert_by_name(self, name: str) -> Optional[DataQualityAlert]:
        """Get a Data Quality alert by name."""
        return self.db.query(DataQualityAlert).filter(DataQualityAlert.name == name).first()
    
    def list_data_quality_alerts(
        self,
        enabled_only: bool = False,
        limit: int = 100
    ) -> Tuple[List[DataQualityAlert], int]:
        """List all Data Quality alerts."""
        query = self.db.query(DataQualityAlert)
        
        if enabled_only:
            query = query.filter(DataQualityAlert.enabled == True)
        
        total = query.count()
        alerts = query.order_by(DataQualityAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update_data_quality_alert(
        self,
        alert_id: str,
        data: DataQualityAlertUpdate
    ) -> Optional[DataQualityAlert]:
        """Update a Data Quality alert."""
        alert = self.get_data_quality_alert(alert_id)
        if not alert:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(alert, key, value)
        
        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def delete_data_quality_alert(self, alert_id: str) -> bool:
        """Delete a Data Quality alert."""
        alert = self.get_data_quality_alert(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    def evaluate_data_quality_alert(self, alert: DataQualityAlert) -> Dict[str, Any]:
        """
        Evaluate a Data Quality alert.
        
        This checks for mock data quality issues based on the alert configuration.
        In production, this would check actual file import logs.
        """
        # Mock data quality issues for demonstration
        mock_issues = self._generate_mock_data_quality_issues(alert)
        
        triggered = len(mock_issues) > 0
        
        if triggered:
            # Create history entry
            for issue in mock_issues[:5]:  # Limit to 5 issues
                history = DataQualityAlertHistory(
                    alert_id=alert.id,
                    file_name=issue.get('file_name'),
                    error_type=issue.get('error_type'),
                    error_details=issue.get('error_details'),
                    affected_records=issue.get('affected_records', 0)
                )
                self.db.add(history)
            
            alert.trigger_count += 1
            alert.last_triggered_at = datetime.utcnow()
            self.db.commit()
        
        return {
            'triggered': triggered,
            'issues_found': len(mock_issues),
            'issues': mock_issues[:10],
            'alert_name': alert.name,
            'quality_type': alert.quality_type
        }
    
    def _generate_mock_data_quality_issues(self, alert: DataQualityAlert) -> List[Dict[str, Any]]:
        """Generate mock data quality issues for demonstration."""
        import random
        
        issues = []
        
        # Generate issues based on quality type
        if alert.quality_type == 'format_error':
            if random.random() > 0.7:
                issues.append({
                    'file_name': f'import_{datetime.now().strftime("%Y%m%d")}.csv',
                    'error_type': 'format_error',
                    'error_details': 'Invalid date format in column "sent_date". Expected YYYY-MM-DD.',
                    'affected_records': random.randint(5, 50)
                })
        
        elif alert.quality_type == 'missing_fields':
            if random.random() > 0.6:
                issues.append({
                    'file_name': f'emails_batch_{random.randint(100, 999)}.csv',
                    'error_type': 'missing_fields',
                    'error_details': 'Required field "sender" is missing in 15 records.',
                    'affected_records': random.randint(10, 30)
                })
        
        elif alert.quality_type == 'encoding_issue':
            if random.random() > 0.8:
                issues.append({
                    'file_name': f'international_emails_{random.randint(1, 10)}.eml',
                    'error_type': 'encoding_issue',
                    'error_details': 'UTF-8 encoding error detected. Some characters could not be decoded.',
                    'affected_records': random.randint(1, 10)
                })
        
        elif alert.quality_type == 'size_limit':
            if alert.file_size_max and random.random() > 0.75:
                issues.append({
                    'file_name': f'large_archive_{random.randint(1, 5)}.pst',
                    'error_type': 'size_limit',
                    'error_details': f'File size ({random.randint(100, 500)}MB) exceeds maximum limit ({alert.file_size_max // (1024*1024)}MB).',
                    'affected_records': 0
                })
        
        elif alert.quality_type == 'corruption':
            if random.random() > 0.9:
                issues.append({
                    'file_name': f'corrupted_file_{random.randint(1, 100)}.eml',
                    'error_type': 'corruption',
                    'error_details': 'File appears to be corrupted. MIME boundary not found.',
                    'affected_records': 1
                })
        
        elif alert.quality_type == 'duplicate_data':
            if random.random() > 0.5:
                issues.append({
                    'file_name': f'import_{datetime.now().strftime("%Y%m%d")}.csv',
                    'error_type': 'duplicate_data',
                    'error_details': f'{random.randint(20, 100)} duplicate email records detected.',
                    'affected_records': random.randint(20, 100)
                })
        
        return issues
    
    # ============ Entity Type Alerts ============
    
    def create_entity_type_alert(self, data: EntityTypeAlertCreate) -> EntityTypeAlert:
        """Create a new Entity Type alert."""
        alert = EntityTypeAlert(
            name=data.name,
            description=data.description,
            entity_type=data.entity_type,
            entity_value=data.entity_value,
            detection_algorithm=data.detection_algorithm,
            dbscan_eps=data.dbscan_eps,
            dbscan_min_samples=data.dbscan_min_samples,
            kmeans_clusters=data.kmeans_clusters,
            sensitivity=data.sensitivity,
            window_hours=data.window_hours,
            baseline_days=data.baseline_days,
            severity=data.severity,
            enabled=data.enabled
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get_entity_type_alert(self, alert_id: str) -> Optional[EntityTypeAlert]:
        """Get an Entity Type alert by ID."""
        return self.db.query(EntityTypeAlert).filter(EntityTypeAlert.id == alert_id).first()
    
    def get_entity_type_alert_by_name(self, name: str) -> Optional[EntityTypeAlert]:
        """Get an Entity Type alert by name."""
        return self.db.query(EntityTypeAlert).filter(EntityTypeAlert.name == name).first()
    
    def list_entity_type_alerts(
        self,
        enabled_only: bool = False,
        limit: int = 100
    ) -> Tuple[List[EntityTypeAlert], int]:
        """List all Entity Type alerts."""
        query = self.db.query(EntityTypeAlert)
        
        if enabled_only:
            query = query.filter(EntityTypeAlert.enabled == True)
        
        total = query.count()
        alerts = query.order_by(EntityTypeAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update_entity_type_alert(
        self,
        alert_id: str,
        data: EntityTypeAlertUpdate
    ) -> Optional[EntityTypeAlert]:
        """Update an Entity Type alert."""
        alert = self.get_entity_type_alert(alert_id)
        if not alert:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(alert, key, value)
        
        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def delete_entity_type_alert(self, alert_id: str) -> bool:
        """Delete an Entity Type alert."""
        alert = self.get_entity_type_alert(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    def evaluate_entity_type_alert(self, alert: EntityTypeAlert) -> Dict[str, Any]:
        """Evaluate an Entity Type alert using DBSCAN or K-Means."""
        result = self.anomaly_service.evaluate_entity_alert(
            entity_type=alert.entity_type,
            entity_value=alert.entity_value,
            algorithm=alert.detection_algorithm,
            window_hours=alert.window_hours,
            baseline_days=alert.baseline_days,
            dbscan_eps=alert.dbscan_eps,
            dbscan_min_samples=alert.dbscan_min_samples,
            kmeans_clusters=alert.kmeans_clusters,
            sensitivity=alert.sensitivity
        )
        
        if result['is_anomaly']:
            # Create history entry
            history = EntityTypeAlertHistory(
                alert_id=alert.id,
                current_value=result['current_value'],
                baseline_value=result['baseline_value'],
                anomaly_score=result['anomaly_score'],
                is_anomaly=True,
                cluster_label=result.get('cluster_label'),
                trigger_reason=result['trigger_reason'],
                top_entities=result.get('top_entities')
            )
            self.db.add(history)
            
            alert.trigger_count += 1
            alert.last_triggered_at = datetime.utcnow()
            self.db.commit()
        
        result['alert_name'] = alert.name
        return result
    
    # ============ Smart AI Alerts ============
    
    def create_smart_ai_alert(self, data: SmartAIAlertCreate) -> SmartAIAlert:
        """Create a new Smart AI alert and parse the description."""
        # Parse the natural language description
        generated_config = self._parse_smart_description(data.description)
        
        alert = SmartAIAlert(
            name=data.name,
            description=data.description,
            generated_config=generated_config.get('config'),
            detected_entities=generated_config.get('entities'),
            detected_keywords=generated_config.get('keywords'),
            detected_patterns=generated_config.get('patterns'),
            detection_algorithm=data.detection_algorithm,
            use_semantic_search=data.use_semantic_search,
            similarity_threshold=data.similarity_threshold,
            severity=data.severity,
            enabled=data.enabled
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def _parse_smart_description(self, description: str) -> Dict[str, Any]:
        """
        Parse natural language description to extract entities, keywords, and patterns.
        
        This is a rule-based parser. In production, you could use an LLM for better parsing.
        """
        description_lower = description.lower()
        
        # Extract potential entity types
        entity_patterns = {
            'PERSON': ['person', 'people', 'employee', 'user', 'individual', 'name'],
            'ORG': ['organization', 'company', 'firm', 'corporation', 'business'],
            'GPE': ['location', 'city', 'country', 'place', 'region'],
            'MONEY': ['money', 'dollar', 'payment', 'amount', 'price', 'cost'],
            'DATE': ['date', 'time', 'deadline', 'schedule'],
            'PRODUCT': ['product', 'service', 'item'],
        }
        
        detected_entities = []
        for entity_type, keywords in entity_patterns.items():
            if any(kw in description_lower for kw in keywords):
                detected_entities.append(entity_type)
        
        # Extract keywords (simple word extraction)
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                      'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                      'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                      'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
                      'above', 'below', 'between', 'under', 'again', 'further', 'then',
                      'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
                      'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                      'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'and',
                      'but', 'if', 'or', 'because', 'as', 'until', 'while', 'alert', 'me',
                      'when', 'i', 'want', 'notify'}
        
        words = re.findall(r'\b[a-z]+\b', description_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Detect patterns
        patterns = []
        if any(word in description_lower for word in ['spike', 'increase', 'surge', 'jump']):
            patterns.append('volume_spike')
        if any(word in description_lower for word in ['drop', 'decrease', 'fall', 'decline']):
            patterns.append('volume_drop')
        if any(word in description_lower for word in ['silence', 'quiet', 'inactive', 'no activity']):
            patterns.append('silence')
        if any(word in description_lower for word in ['unusual', 'anomaly', 'abnormal', 'strange']):
            patterns.append('anomaly')
        if any(word in description_lower for word in ['mention', 'reference', 'discuss']):
            patterns.append('entity_mention')
        
        # Generate config
        config = {
            'monitor_entities': detected_entities or ['ALL'],
            'patterns_to_detect': patterns or ['anomaly'],
            'keywords_to_match': keywords[:10],  # Limit to top 10
            'parsed_at': datetime.utcnow().isoformat()
        }
        
        return {
            'config': config,
            'entities': detected_entities,
            'keywords': keywords[:20],
            'patterns': patterns
        }
    
    def get_smart_ai_alert(self, alert_id: str) -> Optional[SmartAIAlert]:
        """Get a Smart AI alert by ID."""
        return self.db.query(SmartAIAlert).filter(SmartAIAlert.id == alert_id).first()
    
    def get_smart_ai_alert_by_name(self, name: str) -> Optional[SmartAIAlert]:
        """Get a Smart AI alert by name."""
        return self.db.query(SmartAIAlert).filter(SmartAIAlert.name == name).first()
    
    def list_smart_ai_alerts(
        self,
        enabled_only: bool = False,
        limit: int = 100
    ) -> Tuple[List[SmartAIAlert], int]:
        """List all Smart AI alerts."""
        query = self.db.query(SmartAIAlert)
        
        if enabled_only:
            query = query.filter(SmartAIAlert.enabled == True)
        
        total = query.count()
        alerts = query.order_by(SmartAIAlert.created_at.desc()).limit(limit).all()
        
        return alerts, total
    
    def update_smart_ai_alert(
        self,
        alert_id: str,
        data: SmartAIAlertUpdate
    ) -> Optional[SmartAIAlert]:
        """Update a Smart AI alert."""
        alert = self.get_smart_ai_alert(alert_id)
        if not alert:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # If description changed, re-parse it
        if 'description' in update_data:
            generated_config = self._parse_smart_description(update_data['description'])
            update_data['generated_config'] = generated_config.get('config')
            update_data['detected_entities'] = generated_config.get('entities')
            update_data['detected_keywords'] = generated_config.get('keywords')
            update_data['detected_patterns'] = generated_config.get('patterns')
        
        for key, value in update_data.items():
            setattr(alert, key, value)
        
        alert.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def delete_smart_ai_alert(self, alert_id: str) -> bool:
        """Delete a Smart AI alert."""
        alert = self.get_smart_ai_alert(alert_id)
        if not alert:
            return False
        
        self.db.delete(alert)
        self.db.commit()
        return True
    
    def evaluate_smart_ai_alert(self, alert: SmartAIAlert) -> Dict[str, Any]:
        """
        Evaluate a Smart AI alert.
        
        Uses the parsed configuration to check for matching patterns.
        """
        config = alert.generated_config or {}
        keywords = alert.detected_keywords or []
        entities = alert.detected_entities or []
        patterns = alert.detected_patterns or []
        
        # Get recent emails
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)
        
        # Build query based on parsed keywords
        query = self.db.query(Email).filter(
            and_(Email.date >= start_date, Email.date <= end_date)
        )
        
        # Check for keyword matches in subject/body
        matched_emails = []
        emails = query.limit(500).all()
        
        for email in emails:
            match_score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in (email.subject or '').lower() or \
                   keyword.lower() in (email.body or '').lower():
                    match_score += 1
                    matched_keywords.append(keyword)
            
            if match_score > 0:
                matched_emails.append({
                    'email_id': str(email.id),
                    'subject': email.subject,
                    'match_score': match_score / max(1, len(keywords)),
                    'matched_keywords': matched_keywords
                })
        
        # Sort by match score
        matched_emails.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Check entity patterns
        entity_anomaly = False
        if entities:
            for entity_type in entities:
                result = self.anomaly_service.evaluate_entity_alert(
                    entity_type=entity_type,
                    entity_value=None,
                    algorithm=alert.detection_algorithm,
                    window_hours=24,
                    baseline_days=7
                )
                if result['is_anomaly']:
                    entity_anomaly = True
                    break
        
        # Determine if alert should trigger
        triggered = len(matched_emails) > 5 or entity_anomaly
        trigger_reason = None
        
        if triggered:
            if len(matched_emails) > 5:
                trigger_reason = f"Found {len(matched_emails)} emails matching keywords: {', '.join(keywords[:5])}"
            elif entity_anomaly:
                trigger_reason = f"Anomaly detected in entity types: {', '.join(entities)}"
            
            # Create history entry
            history = SmartAIAlertHistory(
                alert_id=alert.id,
                matched_emails=[e['email_id'] for e in matched_emails[:20]],
                match_scores=[e['match_score'] for e in matched_emails[:20]],
                trigger_reason=trigger_reason,
                anomaly_detected=entity_anomaly,
                anomaly_details={
                    'matched_count': len(matched_emails),
                    'entity_anomaly': entity_anomaly
                }
            )
            self.db.add(history)
            
            alert.trigger_count += 1
            alert.last_triggered_at = datetime.utcnow()
            self.db.commit()
        
        return {
            'triggered': triggered,
            'trigger_reason': trigger_reason,
            'matched_emails': matched_emails[:10],
            'entity_anomaly': entity_anomaly,
            'keywords_checked': keywords,
            'entities_checked': entities,
            'alert_name': alert.name
        }
    
    # ============ Dashboard Statistics ============
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for the alerts dashboard."""
        # Count alerts by type
        dq_total = self.db.query(func.count(DataQualityAlert.id)).scalar() or 0
        et_total = self.db.query(func.count(EntityTypeAlert.id)).scalar() or 0
        sa_total = self.db.query(func.count(SmartAIAlert.id)).scalar() or 0
        
        # Count enabled alerts
        dq_enabled = self.db.query(func.count(DataQualityAlert.id)).filter(
            DataQualityAlert.enabled == True
        ).scalar() or 0
        et_enabled = self.db.query(func.count(EntityTypeAlert.id)).filter(
            EntityTypeAlert.enabled == True
        ).scalar() or 0
        sa_enabled = self.db.query(func.count(SmartAIAlert.id)).filter(
            SmartAIAlert.enabled == True
        ).scalar() or 0
        
        # Count triggered in last 24h
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        dq_triggered = self.db.query(func.count(DataQualityAlertHistory.id)).filter(
            DataQualityAlertHistory.triggered_at >= yesterday
        ).scalar() or 0
        et_triggered = self.db.query(func.count(EntityTypeAlertHistory.id)).filter(
            EntityTypeAlertHistory.triggered_at >= yesterday
        ).scalar() or 0
        sa_triggered = self.db.query(func.count(SmartAIAlertHistory.id)).filter(
            SmartAIAlertHistory.triggered_at >= yesterday
        ).scalar() or 0
        
        # Severity breakdown
        by_severity = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        
        for sev in ['low', 'medium', 'high', 'critical']:
            by_severity[sev] += self.db.query(func.count(DataQualityAlert.id)).filter(
                DataQualityAlert.severity == sev
            ).scalar() or 0
            by_severity[sev] += self.db.query(func.count(EntityTypeAlert.id)).filter(
                EntityTypeAlert.severity == sev
            ).scalar() or 0
            by_severity[sev] += self.db.query(func.count(SmartAIAlert.id)).filter(
                SmartAIAlert.severity == sev
            ).scalar() or 0
        
        return {
            'total_data_quality_alerts': dq_total,
            'total_entity_type_alerts': et_total,
            'total_smart_ai_alerts': sa_total,
            'total_alerts': dq_total + et_total + sa_total,
            'enabled_alerts': dq_enabled + et_enabled + sa_enabled,
            'triggered_last_24h': dq_triggered + et_triggered + sa_triggered,
            'anomalies_detected': et_triggered + sa_triggered,
            'by_severity': by_severity
        }
    
    def get_entity_values(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get entity values for dropdown selection."""
        query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label('count')
        ).group_by(Entity.text, Entity.type)
        
        if entity_type and entity_type != 'ALL':
            query = query.filter(Entity.type == entity_type)
        
        query = query.order_by(func.count(Entity.id).desc()).limit(limit)
        
        return [
            {
                'value': r.text,
                'type': r.type,
                'count': r.count
            }
            for r in query.all()
        ]


