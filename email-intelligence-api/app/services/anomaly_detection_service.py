"""Anomaly Detection Service using DBSCAN and K-Means clustering algorithms."""
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
import logging

from app.models.email import Email
from app.models.entity import Entity

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """Service for detecting anomalies in communication patterns using ML clustering."""
    
    # Maximum number of data points to prevent memory issues
    MAX_DATA_POINTS = 3000
    # Threshold days to switch aggregation levels
    DAILY_THRESHOLD_DAYS = 30       # < 30 days: hourly
    WEEKLY_THRESHOLD_DAYS = 365     # 30-365 days: daily
    MONTHLY_THRESHOLD_DAYS = 3650   # 1-10 years: weekly
    # > 10 years: monthly
    
    def __init__(self, db: Session):
        self.db = db
        self.scaler = StandardScaler()
    
    def get_semantic_matching_email_ids(
        self,
        search_query: str,
        similarity_threshold: float = 0.3
    ) -> List[str]:
        """
        Get IDs of emails that semantically match the search query.
        Used for Smart AI alerts to filter activity data.
        """
        from app.core.embeddings import embedding_processor
        from app.core.vector_store import vector_store
        
        print(f"[SEMANTIC] Getting matching email IDs for: {search_query}")
        
        try:
            query_embedding = embedding_processor.encode(search_query)
        except Exception as e:
            logger.error(f"Failed to encode search query: {e}")
            return []
        
        # Search vector store for matching emails
        search_results = vector_store.search(
            query_embedding=query_embedding,
            n_results=1000  # Get up to 1000 matching emails
        )
        
        ids = search_results.get("ids", [])
        distances = search_results.get("distances", [])
        
        print(f"[SEMANTIC] Vector store returned {len(ids)} results")
        
        # Filter by similarity threshold
        matching_ids = []
        for i, email_id in enumerate(ids):
            distance = distances[i] if i < len(distances) else 0
            relevance_score = 1 - distance
            
            if relevance_score >= similarity_threshold:
                matching_ids.append(email_id)
        
        print(f"[SEMANTIC] {len(matching_ids)} emails above threshold {similarity_threshold}")
        return matching_ids
    
    def _get_email_counts_by_ids(
        self,
        email_ids: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Get email counts by time period for specific email IDs.
        Used for Smart AI alerts where we have pre-filtered emails.
        Returns (time_data, aggregation_type)
        """
        if not email_ids:
            return [], 'daily'
        
        # Get emails with these IDs
        emails = self.db.query(Email).filter(Email.id.in_(email_ids)).all()
        print(f"[EMAIL_IDS] Found {len(emails)} emails from {len(email_ids)} IDs")
        
        if not emails:
            return [], 'daily'
        
        # Group by day for Smart AI alerts (simpler aggregation)
        from collections import defaultdict
        daily_counts = defaultdict(lambda: {'count': 0, 'senders': set()})
        
        for email in emails:
            if email.date:
                day_key = email.date.strftime('%Y-%m-%d')
                daily_counts[day_key]['count'] += 1
                if email.sender:
                    daily_counts[day_key]['senders'].add(email.sender)
        
        # Convert to list format
        time_data = []
        for day_str, data in sorted(daily_counts.items()):
            time_data.append({
                'timestamp': datetime.strptime(day_str, '%Y-%m-%d'),
                'email_count': data['count'],
                'unique_senders': len(data['senders'])
            })
        
        print(f"[EMAIL_IDS] Generated {len(time_data)} daily data points")
        return time_data, 'daily'
    
    def get_hourly_email_counts(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hourly email counts with optional entity filtering."""
        # Use SQLite-compatible strftime for hour truncation
        hour_bucket = func.strftime('%Y-%m-%d %H:00:00', Email.date).label('hour')
        
        # Build base query
        query = self.db.query(
            hour_bucket,
            func.count(Email.id).label('email_count'),
            func.count(func.distinct(Email.sender)).label('unique_senders')
        ).filter(
            and_(
                Email.date >= start_date,
                Email.date <= end_date
            )
        )
        
        # Apply entity filtering if specified
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(hour_bucket)
        query = query.order_by(hour_bucket)
        
        results = query.all()
        
        # Convert string hours back to datetime and build result dict
        result_dict = {}
        for r in results:
            try:
                hour_dt = datetime.strptime(r.hour, '%Y-%m-%d %H:%M:%S')
                result_dict[hour_dt] = r
            except (ValueError, TypeError):
                continue
        
        # Fill in missing hours with zeros
        hourly_data = []
        current = start_date.replace(minute=0, second=0, microsecond=0)
        
        while current <= end_date:
            if current in result_dict:
                r = result_dict[current]
                hourly_data.append({
                    'timestamp': current,
                    'email_count': r.email_count,
                    'unique_senders': r.unique_senders
                })
            else:
                hourly_data.append({
                    'timestamp': current,
                    'email_count': 0,
                    'unique_senders': 0
                })
            current += timedelta(hours=1)
        
        return hourly_data
    
    def get_daily_email_counts(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get daily email counts - used for large date ranges to prevent memory issues."""
        # Use SQLite-compatible strftime for day truncation
        day_bucket = func.strftime('%Y-%m-%d', Email.date).label('day')
        
        # Build base query
        query = self.db.query(
            day_bucket,
            func.count(Email.id).label('email_count'),
            func.count(func.distinct(Email.sender)).label('unique_senders')
        ).filter(
            and_(
                Email.date >= start_date,
                Email.date <= end_date
            )
        )
        
        # Apply entity filtering if specified
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(day_bucket)
        query = query.order_by(day_bucket)
        
        results = query.all()
        
        # Convert string days back to datetime and build result dict
        result_dict = {}
        for r in results:
            try:
                day_dt = datetime.strptime(r.day, '%Y-%m-%d')
                result_dict[day_dt.date()] = r
            except (ValueError, TypeError):
                continue
        
        # Fill in missing days with zeros (but limit total days)
        daily_data = []
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
        
        while current <= end_day:
            current_date = current.date()
            if current_date in result_dict:
                r = result_dict[current_date]
                daily_data.append({
                    'timestamp': current,
                    'email_count': r.email_count,
                    'unique_senders': r.unique_senders
                })
            else:
                daily_data.append({
                    'timestamp': current,
                    'email_count': 0,
                    'unique_senders': 0
                })
            current += timedelta(days=1)
            
            # Safety limit to prevent infinite loops
            if len(daily_data) > self.MAX_DATA_POINTS:
                logger.warning(f"Daily data exceeded max points, truncating at {len(daily_data)}")
                break
        
        return daily_data
    
    def get_weekly_email_counts(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get weekly email counts - used for multi-year date ranges."""
        logger.info(f"get_weekly_email_counts: {start_date} to {end_date}")
        
        # Use SQLite-compatible strftime for year-week
        week_bucket = func.strftime('%Y-%W', Email.date).label('week')
        
        query = self.db.query(
            week_bucket,
            func.count(Email.id).label('email_count'),
            func.count(func.distinct(Email.sender)).label('unique_senders'),
            func.min(Email.date).label('week_start')
        ).filter(
            and_(
                Email.date >= start_date,
                Email.date <= end_date,
                Email.date.isnot(None)  # Exclude null dates
            )
        )
        
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(week_bucket)
        query = query.order_by(week_bucket)
        
        results = query.all()
        logger.info(f"Weekly query returned {len(results)} results")
        
        # Build result - only include weeks with data (no zero-fill for weeks)
        weekly_data = []
        for r in results:
            try:
                # Use the actual week_start date from the data
                week_start = r.week_start if r.week_start else datetime.strptime(f"{r.week}-1", '%Y-%W-%w')
                weekly_data.append({
                    'timestamp': week_start,
                    'email_count': r.email_count,
                    'unique_senders': r.unique_senders
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing week {r.week}: {e}")
                continue
            
            if len(weekly_data) > self.MAX_DATA_POINTS:
                break
        
        logger.info(f"Weekly data: {len(weekly_data)} entries")
        return weekly_data
    
    def get_monthly_email_counts(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get monthly email counts - used for decade+ date ranges."""
        logger.info(f"get_monthly_email_counts: {start_date} to {end_date}")
        
        # Use SQLite-compatible strftime for year-month
        month_bucket = func.strftime('%Y-%m', Email.date).label('month')
        
        query = self.db.query(
            month_bucket,
            func.count(Email.id).label('email_count'),
            func.count(func.distinct(Email.sender)).label('unique_senders')
        ).filter(
            and_(
                Email.date >= start_date,
                Email.date <= end_date,
                Email.date.isnot(None)  # Exclude null dates
            )
        )
        
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(month_bucket)
        query = query.order_by(month_bucket)
        
        results = query.all()
        logger.info(f"Monthly query returned {len(results)} results")
        
        # Build result - only include months with data
        monthly_data = []
        for r in results:
            try:
                month_dt = datetime.strptime(r.month + '-01', '%Y-%m-%d')
                monthly_data.append({
                    'timestamp': month_dt,
                    'email_count': r.email_count,
                    'unique_senders': r.unique_senders
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing month {r.month}: {e}")
                continue
            
            if len(monthly_data) > self.MAX_DATA_POINTS:
                break
        
        logger.info(f"Monthly data: {len(monthly_data)} entries")
        return monthly_data
    
    def get_entity_mentions_by_hour(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hourly entity mention counts."""
        # Use SQLite-compatible strftime for hour truncation
        hour_bucket = func.strftime('%Y-%m-%d %H:00:00', Email.date).label('hour')
        
        # SQLite doesn't have array_agg, so we'll use group_concat instead
        query = self.db.query(
            hour_bucket,
            func.count(Entity.id).label('entity_count'),
            func.group_concat(func.distinct(Entity.text)).label('entities')
        ).join(
            Entity, Entity.email_id == Email.id
        ).filter(
            and_(
                Email.date >= start_date,
                Email.date <= end_date
            )
        )
        
        if entity_type and entity_type != 'ALL':
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(hour_bucket)
        query = query.order_by(hour_bucket)
        
        results = []
        for r in query.all():
            try:
                hour_dt = datetime.strptime(r.hour, '%Y-%m-%d %H:%M:%S')
                # Split group_concat result into list
                entities = r.entities.split(',')[:10] if r.entities else []
                results.append({
                    'timestamp': hour_dt,
                    'entity_count': r.entity_count,
                    'entities': entities
                })
            except (ValueError, TypeError):
                continue
        
        return results
    
    def detect_anomalies_dbscan(
        self,
        data: np.ndarray,
        eps: float = 0.5,
        min_samples: int = 3
    ) -> Tuple[np.ndarray, List[int]]:
        """
        Detect anomalies using DBSCAN clustering.
        
        Points labeled as -1 are considered anomalies (noise points).
        
        Args:
            data: Feature matrix (n_samples, n_features)
            eps: Maximum distance between two samples to be considered neighbors
            min_samples: Minimum samples in a neighborhood to form a cluster
            
        Returns:
            Tuple of (labels, anomaly_indices)
        """
        if len(data) < min_samples:
            return np.zeros(len(data)), []
        
        # Normalize the data
        data_scaled = self.scaler.fit_transform(data.reshape(-1, 1) if data.ndim == 1 else data)
        
        # Apply DBSCAN
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(data_scaled)
        
        # Anomalies are points with label -1
        anomaly_indices = np.where(labels == -1)[0].tolist()
        
        return labels, anomaly_indices
    
    def detect_anomalies_kmeans(
        self,
        data: np.ndarray,
        n_clusters: int = 3,
        anomaly_percentile: float = 95
    ) -> Tuple[np.ndarray, List[int], np.ndarray]:
        """
        Detect anomalies using K-Means clustering.
        
        Points far from their cluster center are considered anomalies.
        
        Args:
            data: Feature matrix (n_samples, n_features)
            n_clusters: Number of clusters
            anomaly_percentile: Percentile threshold for anomaly detection
            
        Returns:
            Tuple of (labels, anomaly_indices, distances)
        """
        if len(data) < n_clusters:
            return np.zeros(len(data)), [], np.zeros(len(data))
        
        # Normalize the data
        data_scaled = self.scaler.fit_transform(data.reshape(-1, 1) if data.ndim == 1 else data)
        
        # Apply K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(data_scaled)
        
        # Calculate distances to cluster centers
        distances = np.zeros(len(data_scaled))
        for i, point in enumerate(data_scaled):
            center = kmeans.cluster_centers_[labels[i]]
            distances[i] = np.linalg.norm(point - center)
        
        # Points with distance above threshold are anomalies
        threshold = np.percentile(distances, anomaly_percentile)
        anomaly_indices = np.where(distances > threshold)[0].tolist()
        
        return labels, anomaly_indices, distances
    
    def analyze_communication_activity(
        self,
        hours_back: int = 168,  # 7 days
        algorithm: str = 'dbscan',
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        email_ids: Optional[List[str]] = None,
        dbscan_eps: float = 0.5,
        dbscan_min_samples: int = 3,
        kmeans_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze communication activity and detect anomalies.
        
        Returns activity data with anomaly markers for dashboard visualization.
        email_ids: Optional list of email IDs to filter (for Smart AI semantic search)
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours_back)
        
        return self._analyze_activity(
            start_date, end_date, algorithm, entity_type, entity_value,
            email_ids, dbscan_eps, dbscan_min_samples, kmeans_clusters
        )
    
    def analyze_communication_activity_custom(
        self,
        start_date: datetime,
        end_date: datetime,
        algorithm: str = 'dbscan',
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        email_ids: Optional[List[str]] = None,
        dbscan_eps: float = 0.5,
        dbscan_min_samples: int = 3,
        kmeans_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze communication activity with custom date range.
        email_ids: Optional list of email IDs to filter (for Smart AI semantic search)
        """
        return self._analyze_activity(
            start_date, end_date, algorithm, entity_type, entity_value,
            email_ids, dbscan_eps, dbscan_min_samples, kmeans_clusters
        )
    
    def _analyze_activity(
        self,
        start_date: datetime,
        end_date: datetime,
        algorithm: str = 'dbscan',
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        email_ids: Optional[List[str]] = None,
        dbscan_eps: float = 0.5,
        dbscan_min_samples: int = 3,
        kmeans_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Internal method to analyze communication activity.
        Automatically selects aggregation level based on date range:
        - < 30 days: hourly
        - 30-365 days: daily  
        - 1-10 years: weekly
        - > 10 years: monthly
        
        email_ids: Optional list of email IDs to filter (for Smart AI semantic search)
        """
        
        # Calculate total days to determine aggregation strategy
        total_days = (end_date - start_date).days
        
        # If email_ids provided (Smart AI alert), use filtered counts
        if email_ids:
            print(f"[ACTIVITY] Using email_ids filter with {len(email_ids)} emails")
            time_data, aggregation_type = self._get_email_counts_by_ids(
                email_ids, start_date, end_date
            )
        else:
            # Select aggregation level based on date range
            if total_days > self.MONTHLY_THRESHOLD_DAYS:
                # > 10 years: monthly aggregation
                time_data = self.get_monthly_email_counts(
                    start_date, end_date, entity_type, entity_value
                )
                aggregation_type = 'monthly'
            elif total_days > self.WEEKLY_THRESHOLD_DAYS:
                # 1-10 years: weekly aggregation
                time_data = self.get_weekly_email_counts(
                    start_date, end_date, entity_type, entity_value
                )
                aggregation_type = 'weekly'
            elif total_days > self.DAILY_THRESHOLD_DAYS:
                # 30-365 days: daily aggregation
                time_data = self.get_daily_email_counts(
                    start_date, end_date, entity_type, entity_value
                )
                aggregation_type = 'daily'
            else:
                # < 30 days: hourly aggregation
                time_data = self.get_hourly_email_counts(
                    start_date, end_date, entity_type, entity_value
                )
                aggregation_type = 'hourly'
        
        # Set period_delta based on aggregation_type
        period_delta_map = {
            'monthly': timedelta(days=30),
            'weekly': timedelta(weeks=1),
            'daily': timedelta(days=1),
            'hourly': timedelta(hours=1)
        }
        period_delta = period_delta_map.get(aggregation_type, timedelta(days=1))
        
        logger.info(f"Date range: {total_days} days, using {aggregation_type} aggregation ({len(time_data)} data points)")
        
        # Safety check: limit data points to prevent memory issues
        if len(time_data) > self.MAX_DATA_POINTS:
            logger.warning(f"Data points ({len(time_data)}) exceed max ({self.MAX_DATA_POINTS}), sampling...")
            step = max(1, len(time_data) // self.MAX_DATA_POINTS)
            time_data = time_data[::step]
        
        if not time_data:
            return {
                'data': [],
                'total_emails': 0,
                'total_anomalies': 0,
                'time_range': {'start': start_date, 'end': end_date}
            }
        
        # Extract email counts for anomaly detection
        email_counts = np.array([d['email_count'] for d in time_data])
        
        # Detect anomalies based on selected algorithm
        if algorithm == 'dbscan':
            labels, anomaly_indices = self.detect_anomalies_dbscan(
                email_counts, eps=dbscan_eps, min_samples=dbscan_min_samples
            )
            distances = None
        else:
            labels, anomaly_indices, distances = self.detect_anomalies_kmeans(
                email_counts, n_clusters=kmeans_clusters
            )
        
        # Calculate baseline (mean of non-anomaly points)
        non_anomaly_mask = np.ones(len(email_counts), dtype=bool)
        non_anomaly_mask[anomaly_indices] = False
        baseline = np.mean(email_counts[non_anomaly_mask]) if any(non_anomaly_mask) else np.mean(email_counts)
        
        # Enrich data with anomaly information
        enriched_data = []
        for i, d in enumerate(time_data):
            is_anomaly = i in anomaly_indices
            anomaly_type = None
            anomaly_score = 0.0
            
            if is_anomaly:
                # Determine anomaly type
                if d['email_count'] > baseline * 1.5:
                    anomaly_type = 'spike'
                elif d['email_count'] < baseline * 0.3:
                    anomaly_type = 'silence'
                else:
                    anomaly_type = 'unusual_pattern'
                
                # Calculate anomaly score
                if distances is not None:
                    anomaly_score = float(distances[i])
                else:
                    anomaly_score = abs(d['email_count'] - baseline) / (baseline + 1)
            
            # Get emails for this period based on aggregation type
            period_start = d['timestamp']
            period_end = period_start + period_delta
            email_ids = self._get_email_ids_for_period(period_start, period_end, entity_type, entity_value)
            
            enriched_data.append({
                'timestamp': d['timestamp'].isoformat(),
                'email_count': d['email_count'],
                'unique_senders': d['unique_senders'],
                'is_anomaly': is_anomaly,
                'anomaly_type': anomaly_type,
                'anomaly_score': anomaly_score,
                'cluster_label': int(labels[i]) if labels is not None else None,
                'email_ids': email_ids[:50],  # Limit to 50 emails per hour
                'baseline_value': float(baseline)
            })
        
        return {
            'data': enriched_data,
            'total_emails': int(np.sum(email_counts)),
            'total_anomalies': len(anomaly_indices),
            'baseline': float(baseline),
            'time_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'algorithm': algorithm,
            'aggregation': aggregation_type,
            'data_points': len(enriched_data),
            'parameters': {
                'dbscan_eps': dbscan_eps,
                'dbscan_min_samples': dbscan_min_samples,
                'kmeans_clusters': kmeans_clusters
            }
        }
    
    def _get_email_ids_for_period(
        self,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None
    ) -> List[str]:
        """Get email IDs for a specific time period."""
        query = self.db.query(Email.id).filter(
            and_(Email.date >= start, Email.date < end)
        )
        
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
        
        return [str(r.id) for r in query.all()]
    
    def get_emails_for_data_point(
        self,
        timestamp: datetime,
        limit: int = 50,
        aggregation: str = 'hourly',
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        search_query: Optional[str] = None,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get email details for a specific data point.
        
        Args:
            timestamp: The start time of the data point
            limit: Maximum emails to return
            aggregation: 'hourly', 'daily', 'weekly', or 'monthly'
            entity_type: Filter emails by entity type (e.g., PERSON, ORG)
            entity_value: Filter emails by specific entity value
            search_query: Semantic search query (for Smart AI alerts)
            similarity_threshold: Minimum similarity score for semantic search
        """
        # Determine period based on aggregation type
        if aggregation == 'monthly':
            period_start = timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Get last day of month
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        elif aggregation == 'weekly':
            period_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(weeks=1)
        elif aggregation == 'daily':
            period_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        else:  # hourly
            period_start = timestamp.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
        
        logger.info(f"get_emails_for_data_point: {aggregation} aggregation, {period_start} to {period_end}, entity_type={entity_type}, search_query={search_query}")
        
        # If search_query is provided, use semantic search
        if search_query:
            return self._get_emails_with_semantic_search(
                period_start, period_end, search_query, similarity_threshold, limit
            )
        
        # Build query with optional entity filter
        query = self.db.query(Email).filter(
            and_(Email.date >= period_start, Email.date < period_end)
        )
        
        # Apply entity type filter if specified
        if entity_type and entity_type != 'ALL':
            query = query.join(Entity, Entity.email_id == Email.id)
            query = query.filter(Entity.type == entity_type)
            if entity_value:
                query = query.filter(Entity.text == entity_value)
            # Use distinct to avoid duplicates when joining
            query = query.distinct()
        
        emails = query.limit(limit).all()
        
        result = []
        for email in emails:
            # Get entities for this email
            entities = self.db.query(Entity).filter(Entity.email_id == email.id).all()
            
            # Highlight matched entity if filtering by entity
            matched_entities = []
            other_entities = []
            for e in entities:
                entity_dict = {'type': e.type, 'text': e.text}
                if entity_type and e.type == entity_type:
                    if not entity_value or e.text == entity_value:
                        matched_entities.append(entity_dict)
                    else:
                        other_entities.append(entity_dict)
                else:
                    other_entities.append(entity_dict)
            
            # Put matched entities first
            all_entities = matched_entities + other_entities
            
            result.append({
                'id': str(email.id),
                'subject': email.subject,
                'sender': email.sender,
                'recipients': email.recipients.split(',') if email.recipients else [],
                'date': email.date.isoformat() if email.date else None,
                'body_preview': email.body[:200] if email.body else None,
                'entities': all_entities[:20],
                'matched_entity_count': len(matched_entities)
            })
        
        return result
    
    def _get_emails_with_semantic_search(
        self,
        period_start: datetime,
        period_end: datetime,
        search_query: str,
        similarity_threshold: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get emails using semantic search within a time period."""
        from app.core.embeddings import embedding_processor
        from app.core.vector_store import vector_store
        
        logger.info(f"Semantic search: '{search_query}' in period {period_start} to {period_end}, threshold={similarity_threshold}")
        print(f"[SEMANTIC SEARCH] Query: '{search_query}', Period: {period_start} to {period_end}, Threshold: {similarity_threshold}")
        
        # Generate query embedding
        try:
            query_embedding = embedding_processor.encode(search_query)
        except Exception as e:
            logger.error(f"Failed to encode search query: {e}")
            # Fall back to regular query if embedding fails
            emails = self.db.query(Email).filter(
                and_(Email.date >= period_start, Email.date < period_end)
            ).limit(limit).all()
            return self._format_email_results(emails)
        
        # Search in vector store - get many results since we'll filter by date
        search_results = vector_store.search(
            query_embedding=query_embedding,
            n_results=500  # Get lots of results to filter by date
        )
        
        ids = search_results.get("ids", [])
        distances = search_results.get("distances", [])
        
        logger.info(f"Vector search returned {len(ids)} results")
        print(f"[SEMANTIC SEARCH] Vector store returned {len(ids)} results")
        
        # If vector store is empty or returns no results, fall back to regular query
        if not ids:
            logger.warning("Vector store returned no results - falling back to regular DB query")
            emails = self.db.query(Email).filter(
                and_(Email.date >= period_start, Email.date < period_end)
            ).limit(limit).all()
            if emails:
                return self._format_email_results(emails)
            # If still no emails in period, get ANY emails
            emails = self.db.query(Email).order_by(Email.date.desc()).limit(limit).all()
            return self._format_email_results(emails)
        
        # Filter by date and similarity
        result = []
        date_filtered = 0
        similarity_filtered = 0
        
        for i, email_id in enumerate(ids):
            email = self.db.query(Email).filter(Email.id == email_id).first()
            if not email:
                continue
            
            # Calculate relevance score
            distance = distances[i] if i < len(distances) else 0
            relevance_score = 1 - distance
            
            # Apply similarity threshold first
            if relevance_score < similarity_threshold:
                similarity_filtered += 1
                continue
            
            # Check date range
            if email.date:
                if email.date < period_start or email.date >= period_end:
                    date_filtered += 1
                    continue
            
            # Get entities for this email
            entities = self.db.query(Entity).filter(Entity.email_id == email.id).all()
            
            result.append({
                'id': str(email.id),
                'subject': email.subject,
                'sender': email.sender,
                'recipients': email.recipients.split(',') if email.recipients else [],
                'date': email.date.isoformat() if email.date else None,
                'body_preview': email.body[:200] if email.body else None,
                'entities': [{'type': e.type, 'text': e.text} for e in entities[:20]],
                'relevance_score': round(relevance_score, 4),
                'matched_entity_count': 0
            })
            
            if len(result) >= limit:
                break
        
        # Sort by relevance score
        result.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        logger.info(f"Semantic search: {len(result)} emails found, {date_filtered} filtered by date, {similarity_filtered} filtered by similarity")
        print(f"[SEMANTIC SEARCH] Result: {len(result)} emails, {date_filtered} date-filtered, {similarity_filtered} similarity-filtered")
        
        # If no results in time period, return top semantic matches regardless of date
        if not result and len(ids) > 0:
            logger.warning(f"No emails in time period - returning top semantic matches ignoring date filter")
            # Use a lower threshold for fallback
            fallback_threshold = min(similarity_threshold, 0.3)
            for i, email_id in enumerate(ids[:limit * 2]):
                email = self.db.query(Email).filter(Email.id == email_id).first()
                if not email:
                    continue
                
                distance = distances[i] if i < len(distances) else 0
                relevance_score = 1 - distance
                
                if relevance_score < fallback_threshold:
                    continue
                
                entities = self.db.query(Entity).filter(Entity.email_id == email.id).all()
                
                result.append({
                    'id': str(email.id),
                    'subject': email.subject,
                    'sender': email.sender,
                    'recipients': email.recipients.split(',') if email.recipients else [],
                    'date': email.date.isoformat() if email.date else None,
                    'body_preview': email.body[:200] if email.body else None,
                    'entities': [{'type': e.type, 'text': e.text} for e in entities[:20]],
                    'relevance_score': round(relevance_score, 4),
                    'matched_entity_count': 0,
                    'note': 'Best semantic match (from any time period)'
                })
                
                if len(result) >= limit:
                    break
            
            result.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Still no results? Return ANY emails that semantically match, very permissive
        if not result and len(ids) > 0:
            logger.warning(f"Still no results - returning any semantic matches")
            for i, email_id in enumerate(ids[:limit]):
                email = self.db.query(Email).filter(Email.id == email_id).first()
                if not email:
                    continue
                
                distance = distances[i] if i < len(distances) else 0
                relevance_score = 1 - distance
                
                entities = self.db.query(Entity).filter(Entity.email_id == email.id).all()
                
                result.append({
                    'id': str(email.id),
                    'subject': email.subject,
                    'sender': email.sender,
                    'recipients': email.recipients.split(',') if email.recipients else [],
                    'date': email.date.isoformat() if email.date else None,
                    'body_preview': email.body[:200] if email.body else None,
                    'entities': [{'type': e.type, 'text': e.text} for e in entities[:20]],
                    'relevance_score': round(relevance_score, 4),
                    'matched_entity_count': 0,
                    'note': f'Semantic match (score: {round(relevance_score * 100)}%)'
                })
        
        return result
    
    def _format_email_results(self, emails: List) -> List[Dict[str, Any]]:
        """Format email query results."""
        result = []
        for email in emails:
            entities = self.db.query(Entity).filter(Entity.email_id == email.id).all()
            result.append({
                'id': str(email.id),
                'subject': email.subject,
                'sender': email.sender,
                'recipients': email.recipients.split(',') if email.recipients else [],
                'date': email.date.isoformat() if email.date else None,
                'body_preview': email.body[:200] if email.body else None,
                'entities': [{'type': e.type, 'text': e.text} for e in entities[:20]],
                'matched_entity_count': 0
            })
        return result
    
    def evaluate_entity_alert(
        self,
        entity_type: str,
        entity_value: Optional[str],
        algorithm: str,
        window_hours: int,
        baseline_days: int,
        dbscan_eps: float = 0.5,
        dbscan_min_samples: int = 3,
        kmeans_clusters: int = 3,
        sensitivity: float = 1.5
    ) -> Dict[str, Any]:
        """
        Evaluate an entity type alert using the specified algorithm.
        
        Returns detection result with current value, baseline, and whether it triggered.
        """
        end_date = datetime.utcnow()
        
        # Get current window data
        window_start = end_date - timedelta(hours=window_hours)
        current_data = self.get_entity_mentions_by_hour(
            window_start, end_date, entity_type, entity_value
        )
        current_count = sum(d['entity_count'] for d in current_data)
        
        # Get baseline data
        baseline_start = window_start - timedelta(days=baseline_days)
        baseline_data = self.get_entity_mentions_by_hour(
            baseline_start, window_start, entity_type, entity_value
        )
        
        if not baseline_data:
            baseline_count = 0
            baseline_hourly = 0
        else:
            baseline_count = sum(d['entity_count'] for d in baseline_data)
            baseline_hourly = baseline_count / (baseline_days * 24)
        
        current_hourly = current_count / window_hours if window_hours > 0 else 0
        
        # Build feature matrix for anomaly detection
        all_counts = np.array([d['entity_count'] for d in baseline_data + current_data])
        
        if len(all_counts) < 3:
            return {
                'is_anomaly': False,
                'anomaly_type': None,
                'anomaly_score': 0.0,
                'current_value': current_hourly,
                'baseline_value': baseline_hourly,
                'trigger_reason': 'Insufficient data for analysis'
            }
        
        # Detect anomalies
        if algorithm == 'dbscan':
            labels, anomaly_indices = self.detect_anomalies_dbscan(
                all_counts, eps=dbscan_eps / sensitivity, min_samples=dbscan_min_samples
            )
            # Check if current window points are anomalies
            current_start_idx = len(baseline_data)
            is_anomaly = any(i in anomaly_indices for i in range(current_start_idx, len(all_counts)))
            anomaly_score = len([i for i in anomaly_indices if i >= current_start_idx]) / max(1, len(current_data))
        else:
            labels, anomaly_indices, distances = self.detect_anomalies_kmeans(
                all_counts, n_clusters=kmeans_clusters, anomaly_percentile=100 - (100 / sensitivity)
            )
            current_start_idx = len(baseline_data)
            is_anomaly = any(i in anomaly_indices for i in range(current_start_idx, len(all_counts)))
            anomaly_score = np.mean(distances[current_start_idx:]) if len(distances) > current_start_idx else 0
        
        # Determine anomaly type
        anomaly_type = None
        trigger_reason = None
        
        if is_anomaly:
            change_pct = ((current_hourly - baseline_hourly) / (baseline_hourly + 0.001)) * 100
            
            if change_pct > 50:
                anomaly_type = 'spike'
                trigger_reason = f"Entity mentions spiked by {change_pct:.1f}% compared to baseline"
            elif change_pct < -50:
                anomaly_type = 'silence'
                trigger_reason = f"Entity mentions dropped by {abs(change_pct):.1f}% (possible silence)"
            else:
                anomaly_type = 'unusual_pattern'
                trigger_reason = f"Unusual pattern detected in entity mention distribution"
        
        # Get top entities contributing to anomaly
        top_entities = []
        if current_data:
            entity_counts = {}
            for d in current_data:
                for e in d.get('entities', []):
                    entity_counts[e] = entity_counts.get(e, 0) + 1
            top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_type': anomaly_type,
            'anomaly_score': float(anomaly_score),
            'cluster_label': int(labels[-1]) if labels is not None and len(labels) > 0 else None,
            'current_value': float(current_hourly),
            'baseline_value': float(baseline_hourly),
            'trigger_reason': trigger_reason,
            'top_entities': [{'entity': e, 'count': c} for e, c in top_entities],
            'algorithm': algorithm,
            'window_hours': window_hours,
            'baseline_days': baseline_days
        }
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently triggered alerts across all alert types."""
        from app.models.unified_alert import (
            DataQualityAlert, DataQualityAlertHistory,
            EntityTypeAlert, EntityTypeAlertHistory,
            SmartAIAlert, SmartAIAlertHistory
        )
        
        alerts = []
        
        # Get Data Quality alert history
        dq_history = self.db.query(
            DataQualityAlertHistory, DataQualityAlert
        ).join(
            DataQualityAlert
        ).order_by(
            DataQualityAlertHistory.triggered_at.desc()
        ).limit(limit).all()
        
        for hist, alert in dq_history:
            alerts.append({
                'id': hist.id,
                'alert_name': alert.name,
                'alert_type': 'data_quality',
                'triggered_at': hist.triggered_at.isoformat(),
                'severity': alert.severity,
                'anomaly_type': hist.error_type,
                'trigger_reason': hist.error_details
            })
        
        # Get Entity Type alert history
        et_history = self.db.query(
            EntityTypeAlertHistory, EntityTypeAlert
        ).join(
            EntityTypeAlert
        ).order_by(
            EntityTypeAlertHistory.triggered_at.desc()
        ).limit(limit).all()
        
        for hist, alert in et_history:
            alerts.append({
                'id': hist.id,
                'alert_name': alert.name,
                'alert_type': 'entity_type',
                'triggered_at': hist.triggered_at.isoformat(),
                'severity': alert.severity,
                'anomaly_type': 'anomaly' if hist.is_anomaly else None,
                'trigger_reason': hist.trigger_reason
            })
        
        # Get Smart AI alert history
        sa_history = self.db.query(
            SmartAIAlertHistory, SmartAIAlert
        ).join(
            SmartAIAlert
        ).order_by(
            SmartAIAlertHistory.triggered_at.desc()
        ).limit(limit).all()
        
        for hist, alert in sa_history:
            alerts.append({
                'id': hist.id,
                'alert_name': alert.name,
                'alert_type': 'smart_ai',
                'triggered_at': hist.triggered_at.isoformat(),
                'severity': alert.severity,
                'anomaly_type': 'smart_detection' if hist.anomaly_detected else None,
                'trigger_reason': hist.trigger_reason
            })
        
        # Sort by triggered_at descending
        alerts.sort(key=lambda x: x['triggered_at'], reverse=True)
        
        return alerts[:limit]

