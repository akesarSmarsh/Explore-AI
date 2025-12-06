"""Unified Alerts API - Data Quality, Entity Type, and Smart AI alert endpoints."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.unified_alert_service import UnifiedAlertService
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.schemas.unified_alert import (
    # Data Quality
    DataQualityAlertCreate, DataQualityAlertUpdate,
    DataQualityAlertResponse, DataQualityAlertListResponse,
    # Entity Type
    EntityTypeAlertCreate, EntityTypeAlertUpdate,
    EntityTypeAlertResponse, EntityTypeAlertListResponse,
    # Smart AI
    SmartAIAlertCreate, SmartAIAlertUpdate,
    SmartAIAlertResponse, SmartAIAlertListResponse,
    # Dashboard
    UnifiedAlertFormOptions, AlertsDashboardStats,
    CommunicationActivityResponse, DataPointEmailsResponse,
    RecentAlertsResponse
)

router = APIRouter()


# ============ Form Options ============

@router.get("/options", response_model=UnifiedAlertFormOptions)
def get_form_options():
    """Get all form options for alert creation dropdowns."""
    return UnifiedAlertFormOptions()


@router.get("/stats", response_model=AlertsDashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get statistics for the alerts dashboard."""
    service = UnifiedAlertService(db)
    stats = service.get_dashboard_stats()
    return AlertsDashboardStats(**stats)


@router.get("/entity-values")
def get_entity_values(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get available entity values for dropdown selection."""
    service = UnifiedAlertService(db)
    values = service.get_entity_values(entity_type=entity_type, limit=limit)
    return {"total": len(values), "entity_values": values}


# ============ Data Quality Alerts ============

@router.get("/data-quality", response_model=DataQualityAlertListResponse)
def list_data_quality_alerts(
    enabled_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all Data Quality alerts."""
    service = UnifiedAlertService(db)
    alerts, total = service.list_data_quality_alerts(enabled_only=enabled_only, limit=limit)
    return DataQualityAlertListResponse(
        total=total,
        alerts=[DataQualityAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("/data-quality", response_model=DataQualityAlertResponse)
def create_data_quality_alert(
    data: DataQualityAlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Data Quality alert.
    
    Monitors file imports for data quality issues like:
    - Format errors
    - Missing required fields
    - Encoding issues
    - File size limits
    - Data corruption
    - Duplicate data
    """
    service = UnifiedAlertService(db)
    
    existing = service.get_data_quality_alert_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create_data_quality_alert(data)
    return DataQualityAlertResponse.model_validate(alert)


@router.get("/data-quality/{alert_id}", response_model=DataQualityAlertResponse)
def get_data_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific Data Quality alert."""
    service = UnifiedAlertService(db)
    alert = service.get_data_quality_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return DataQualityAlertResponse.model_validate(alert)


@router.put("/data-quality/{alert_id}", response_model=DataQualityAlertResponse)
def update_data_quality_alert(
    alert_id: str,
    data: DataQualityAlertUpdate,
    db: Session = Depends(get_db)
):
    """Update a Data Quality alert."""
    service = UnifiedAlertService(db)
    alert = service.update_data_quality_alert(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return DataQualityAlertResponse.model_validate(alert)


@router.delete("/data-quality/{alert_id}")
def delete_data_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete a Data Quality alert."""
    service = UnifiedAlertService(db)
    success = service.delete_data_quality_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted successfully", "alert_id": alert_id}


@router.patch("/data-quality/{alert_id}/toggle")
def toggle_data_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    """Toggle a Data Quality alert's enabled status."""
    service = UnifiedAlertService(db)
    alert = service.get_data_quality_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.enabled = not alert.enabled
    db.commit()
    
    return {"alert_id": alert_id, "enabled": alert.enabled}


@router.post("/data-quality/{alert_id}/evaluate")
def evaluate_data_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    """Evaluate a Data Quality alert for issues."""
    service = UnifiedAlertService(db)
    alert = service.get_data_quality_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = service.evaluate_data_quality_alert(alert)
    return result


# ============ Entity Type Alerts ============

@router.get("/entity-type", response_model=EntityTypeAlertListResponse)
def list_entity_type_alerts(
    enabled_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all Entity Type alerts."""
    service = UnifiedAlertService(db)
    alerts, total = service.list_entity_type_alerts(enabled_only=enabled_only, limit=limit)
    return EntityTypeAlertListResponse(
        total=total,
        alerts=[EntityTypeAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("/entity-type", response_model=EntityTypeAlertResponse)
def create_entity_type_alert(
    data: EntityTypeAlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Entity Type alert.
    
    Uses DBSCAN or K-Means clustering for anomaly detection in entity mentions.
    
    ## Algorithm Options
    
    - **DBSCAN**: Density-based clustering that identifies outliers as noise points
      - eps: Maximum distance between points in a cluster (lower = more sensitive)
      - min_samples: Minimum points to form a cluster
      
    - **K-Means**: Partitions data into K clusters, anomalies are far from centers
      - kmeans_clusters: Number of clusters
      - Uses distance to cluster center for anomaly scoring
    """
    service = UnifiedAlertService(db)
    
    existing = service.get_entity_type_alert_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create_entity_type_alert(data)
    return EntityTypeAlertResponse.model_validate(alert)


@router.get("/entity-type/{alert_id}", response_model=EntityTypeAlertResponse)
def get_entity_type_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific Entity Type alert."""
    service = UnifiedAlertService(db)
    alert = service.get_entity_type_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return EntityTypeAlertResponse.model_validate(alert)


@router.put("/entity-type/{alert_id}", response_model=EntityTypeAlertResponse)
def update_entity_type_alert(
    alert_id: str,
    data: EntityTypeAlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an Entity Type alert."""
    service = UnifiedAlertService(db)
    alert = service.update_entity_type_alert(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return EntityTypeAlertResponse.model_validate(alert)


@router.delete("/entity-type/{alert_id}")
def delete_entity_type_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete an Entity Type alert."""
    service = UnifiedAlertService(db)
    success = service.delete_entity_type_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted successfully", "alert_id": alert_id}


@router.patch("/entity-type/{alert_id}/toggle")
def toggle_entity_type_alert(alert_id: str, db: Session = Depends(get_db)):
    """Toggle an Entity Type alert's enabled status."""
    service = UnifiedAlertService(db)
    alert = service.get_entity_type_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.enabled = not alert.enabled
    db.commit()
    
    return {"alert_id": alert_id, "enabled": alert.enabled}


@router.post("/entity-type/{alert_id}/evaluate")
def evaluate_entity_type_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Evaluate an Entity Type alert using DBSCAN or K-Means.
    
    Returns anomaly detection results including:
    - Whether an anomaly was detected
    - Anomaly type (spike, silence, unusual_pattern)
    - Anomaly score
    - Current vs baseline values
    - Top contributing entities
    """
    service = UnifiedAlertService(db)
    alert = service.get_entity_type_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = service.evaluate_entity_type_alert(alert)
    return result


# ============ Smart AI Alerts ============

@router.get("/smart-ai", response_model=SmartAIAlertListResponse)
def list_smart_ai_alerts(
    enabled_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all Smart AI alerts."""
    service = UnifiedAlertService(db)
    alerts, total = service.list_smart_ai_alerts(enabled_only=enabled_only, limit=limit)
    return SmartAIAlertListResponse(
        total=total,
        alerts=[SmartAIAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("/smart-ai", response_model=SmartAIAlertResponse)
def create_smart_ai_alert(
    data: SmartAIAlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Smart AI alert.
    
    Provide a natural language description of what you want to monitor.
    The system will automatically:
    - Extract entities to monitor
    - Identify keywords to match
    - Detect patterns to look for
    
    ## Example Descriptions
    
    - "Alert me when there's unusual activity mentioning specific people"
    - "Notify when money amounts spike in communications"
    - "Watch for sudden silence from key organizations"
    """
    service = UnifiedAlertService(db)
    
    existing = service.get_smart_ai_alert_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create_smart_ai_alert(data)
    return SmartAIAlertResponse.model_validate(alert)


@router.get("/smart-ai/{alert_id}", response_model=SmartAIAlertResponse)
def get_smart_ai_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific Smart AI alert."""
    service = UnifiedAlertService(db)
    alert = service.get_smart_ai_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SmartAIAlertResponse.model_validate(alert)


@router.put("/smart-ai/{alert_id}", response_model=SmartAIAlertResponse)
def update_smart_ai_alert(
    alert_id: str,
    data: SmartAIAlertUpdate,
    db: Session = Depends(get_db)
):
    """Update a Smart AI alert. If description changes, it will be re-parsed."""
    service = UnifiedAlertService(db)
    alert = service.update_smart_ai_alert(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SmartAIAlertResponse.model_validate(alert)


@router.delete("/smart-ai/{alert_id}")
def delete_smart_ai_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete a Smart AI alert."""
    service = UnifiedAlertService(db)
    success = service.delete_smart_ai_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted successfully", "alert_id": alert_id}


@router.patch("/smart-ai/{alert_id}/toggle")
def toggle_smart_ai_alert(alert_id: str, db: Session = Depends(get_db)):
    """Toggle a Smart AI alert's enabled status."""
    service = UnifiedAlertService(db)
    alert = service.get_smart_ai_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.enabled = not alert.enabled
    db.commit()
    
    return {"alert_id": alert_id, "enabled": alert.enabled}


@router.post("/smart-ai/{alert_id}/evaluate")
def evaluate_smart_ai_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Evaluate a Smart AI alert.
    
    Checks for matches based on the parsed description:
    - Keyword matches in emails
    - Entity pattern anomalies
    - Semantic similarity (if enabled)
    """
    service = UnifiedAlertService(db)
    alert = service.get_smart_ai_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = service.evaluate_smart_ai_alert(alert)
    return result


# ============ Dashboard APIs ============

@router.get("/dashboard/debug-emails")
def debug_email_dates(db: Session = Depends(get_db)):
    """Debug endpoint to check email dates."""
    from app.models.email import Email
    from sqlalchemy import func
    
    # Get total count
    total = db.query(func.count(Email.id)).scalar()
    
    # Get count with valid dates
    with_dates = db.query(func.count(Email.id)).filter(Email.date.isnot(None)).scalar()
    
    # Get sample emails
    samples = db.query(Email.id, Email.date, Email.subject).limit(10).all()
    
    return {
        'total_emails': total,
        'emails_with_dates': with_dates,
        'emails_without_dates': total - with_dates,
        'sample_emails': [
            {
                'id': s.id,
                'date': s.date.isoformat() if s.date else None,
                'date_type': str(type(s.date)),
                'subject': s.subject[:50] if s.subject else None
            }
            for s in samples
        ]
    }


@router.get("/dashboard/date-range")
def get_data_date_range(db: Session = Depends(get_db)):
    """
    Get the date range of available email data.
    
    Useful for setting appropriate date ranges when data is old.
    """
    from app.models.email import Email
    from sqlalchemy import func
    
    result = db.query(
        func.min(Email.date).label('min_date'),
        func.max(Email.date).label('max_date'),
        func.count(Email.id).label('total_emails')
    ).first()
    
    return {
        'min_date': result.min_date.isoformat() if result.min_date else None,
        'max_date': result.max_date.isoformat() if result.max_date else None,
        'total_emails': result.total_emails or 0
    }


@router.get("/dashboard/activity")
def get_communication_activity(
    hours_back: int = Query(168, ge=1, le=876000, description="Hours of data to retrieve (ignored if start_date/end_date provided)"),
    start_date: Optional[str] = Query(None, description="Custom start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Custom end date (ISO format)"),
    use_all_data: bool = Query(False, description="Use full date range of available data"),
    algorithm: str = Query("dbscan", pattern="^(dbscan|kmeans)$"),
    entity_type: Optional[str] = Query(None),
    entity_value: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None, description="Semantic search query for Smart AI alerts"),
    similarity_threshold: float = Query(0.3, ge=0.1, le=1.0, description="Similarity threshold for semantic search"),
    dbscan_eps: float = Query(0.5, ge=0.1, le=5.0),
    dbscan_min_samples: int = Query(3, ge=1, le=20),
    kmeans_clusters: int = Query(3, ge=2, le=10),
    db: Session = Depends(get_db)
):
    """
    Get communication activity data for the dashboard chart.
    
    Supports:
    - hours_back: Get data for last N hours from now
    - start_date/end_date: Custom date range (ISO format)
    - use_all_data: Use full date range of available emails in database
    
    Returns hourly email counts with anomaly detection using DBSCAN or K-Means.
    """
    from datetime import datetime
    from sqlalchemy import func
    from app.models.email import Email
    import logging
    
    logger = logging.getLogger(__name__)
    service = AnomalyDetectionService(db)
    
    # First, get total email count and date range for debugging
    total_emails = db.query(func.count(Email.id)).scalar()
    logger.info(f"Total emails in database: {total_emails}")
    
    # Handle Smart AI alerts with semantic search
    matching_email_ids = None
    if search_query:
        logger.info(f"Smart AI alert - performing semantic search for: {search_query}")
        print(f"[ACTIVITY] Smart AI semantic search: {search_query}")
        matching_email_ids = service.get_semantic_matching_email_ids(search_query, similarity_threshold)
        logger.info(f"Found {len(matching_email_ids)} semantically matching emails")
        print(f"[ACTIVITY] Found {len(matching_email_ids)} matching emails")
        
        if not matching_email_ids:
            return {
                'data': [],
                'total_emails': 0,
                'total_anomalies': 0,
                'aggregation': 'daily',
                'time_range': {'start': None, 'end': None},
                'message': f'No emails matching "{search_query}" found'
            }
    
    # Option 1: Use all available data from database
    if use_all_data:
        date_range = db.query(
            func.min(Email.date).label('min_date'),
            func.max(Email.date).label('max_date')
        ).filter(Email.date.isnot(None)).first()
        
        logger.info(f"Date range query result: min={date_range.min_date}, max={date_range.max_date}")
        
        if date_range.min_date and date_range.max_date:
            result = service.analyze_communication_activity_custom(
                start_date=date_range.min_date,
                end_date=date_range.max_date,
                algorithm=algorithm,
                entity_type=entity_type,
                entity_value=entity_value,
                email_ids=matching_email_ids,
                dbscan_eps=dbscan_eps,
                dbscan_min_samples=dbscan_min_samples,
                kmeans_clusters=kmeans_clusters
            )
            return result
        else:
            # No data with valid dates
            return {
                'data': [],
                'total_emails': 0,
                'total_anomalies': 0,
                'time_range': {'start': None, 'end': None},
                'message': 'No emails with valid dates found in database'
            }
    
    # Option 2: Custom date range
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00').replace('T', ' ').split('+')[0])
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00').replace('T', ' ').split('+')[0])
            
            result = service.analyze_communication_activity_custom(
                start_date=start_dt,
                end_date=end_dt,
                algorithm=algorithm,
                entity_type=entity_type,
                entity_value=entity_value,
                email_ids=matching_email_ids,
                dbscan_eps=dbscan_eps,
                dbscan_min_samples=dbscan_min_samples,
                kmeans_clusters=kmeans_clusters
            )
            return result
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    
    # Option 3: Use hours_back relative to latest email date (for historical data support)
    # Get latest email date as reference point instead of current time
    latest_email_date = db.query(func.max(Email.date)).scalar()
    
    if latest_email_date:
        # Use latest email date as the end point, respect hours_back window
        result = service.analyze_communication_activity(
            hours_back=hours_back,
            algorithm=algorithm,
            entity_type=entity_type,
            entity_value=entity_value,
            email_ids=matching_email_ids,
            dbscan_eps=dbscan_eps,
            dbscan_min_samples=dbscan_min_samples,
            kmeans_clusters=kmeans_clusters
        )
        return result
    
    # Fallback if no emails exist
    result = service.analyze_communication_activity(
        hours_back=hours_back,
        algorithm=algorithm,
        entity_type=entity_type,
        entity_value=entity_value,
        email_ids=matching_email_ids,
        dbscan_eps=dbscan_eps,
        dbscan_min_samples=dbscan_min_samples,
        kmeans_clusters=kmeans_clusters
    )
    return result


@router.get("/dashboard/data-point-emails")
def get_data_point_emails(
    timestamp: str = Query(..., description="ISO format timestamp of the data point"),
    aggregation: str = Query("hourly", pattern="^(hourly|daily|weekly|monthly)$", description="Aggregation type used in the chart"),
    entity_type: Optional[str] = Query(None, description="Entity type filter (e.g., PERSON, ORG)"),
    entity_value: Optional[str] = Query(None, description="Entity value filter"),
    search_query: Optional[str] = Query(None, description="Semantic search query (for Smart AI alerts)"),
    similarity_threshold: float = Query(0.5, ge=0.1, le=1.0, description="Minimum similarity score for semantic search"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get email details for a specific data point in the chart.
    
    When user clicks on a data point in the communication activity chart,
    this endpoint returns the emails for that time period.
    
    **aggregation** parameter should match the aggregation type from the activity response:
    - hourly: for date ranges < 30 days
    - daily: for date ranges 30-365 days  
    - weekly: for date ranges 1-10 years
    - monthly: for date ranges > 10 years
    
    **entity_type** and **entity_value** should match the filters used in the activity query.
    
    **search_query** enables semantic search for Smart AI alerts - returns emails semantically related to the query.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Handle various timestamp formats
        ts_clean = timestamp.replace('Z', '').replace('T', ' ').split('+')[0]
        ts = datetime.fromisoformat(ts_clean)
        logger.info(f"Parsed timestamp: {ts}, aggregation: {aggregation}, entity_type: {entity_type}, search_query: {search_query}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")
    
    service = AnomalyDetectionService(db)
    emails = service.get_emails_for_data_point(
        ts, 
        limit=limit, 
        aggregation=aggregation,
        entity_type=entity_type,
        entity_value=entity_value,
        search_query=search_query,
        similarity_threshold=similarity_threshold
    )
    
    logger.info(f"Found {len(emails)} emails for timestamp {ts} with {aggregation} aggregation")
    
    return {
        'timestamp': timestamp,
        'aggregation': aggregation,
        'entity_type': entity_type,
        'entity_value': entity_value,
        'search_query': search_query,
        'email_count': len(emails),
        'emails': emails
    }


@router.get("/dashboard/recent-alerts", response_model=RecentAlertsResponse)
def get_recent_alerts(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get recently triggered alerts across all types."""
    service = AnomalyDetectionService(db)
    alerts = service.get_recent_alerts(limit=limit)
    return RecentAlertsResponse(total=len(alerts), alerts=alerts)


@router.post("/evaluate-all")
def evaluate_all_alerts(db: Session = Depends(get_db)):
    """Evaluate all enabled alerts and return triggered ones."""
    service = UnifiedAlertService(db)
    triggered = []
    
    # Evaluate Data Quality alerts
    dq_alerts, _ = service.list_data_quality_alerts(enabled_only=True)
    for alert in dq_alerts:
        result = service.evaluate_data_quality_alert(alert)
        if result.get('triggered'):
            triggered.append({
                'alert_type': 'data_quality',
                'alert_name': alert.name,
                **result
            })
    
    # Evaluate Entity Type alerts
    et_alerts, _ = service.list_entity_type_alerts(enabled_only=True)
    for alert in et_alerts:
        result = service.evaluate_entity_type_alert(alert)
        if result.get('is_anomaly'):
            triggered.append({
                'alert_type': 'entity_type',
                'alert_name': alert.name,
                **result
            })
    
    # Evaluate Smart AI alerts
    sa_alerts, _ = service.list_smart_ai_alerts(enabled_only=True)
    for alert in sa_alerts:
        result = service.evaluate_smart_ai_alert(alert)
        if result.get('triggered'):
            triggered.append({
                'alert_type': 'smart_ai',
                'alert_name': alert.name,
                **result
            })
    
    return {
        'evaluated': True,
        'triggered_count': len(triggered),
        'triggered_alerts': triggered
    }


# ============ Email Notification Testing ============

@router.post("/test-email")
def test_email_notification(
    recipient: str = Query(..., description="Email address to send test to"),
    db: Session = Depends(get_db)
):
    """
    Send a test email notification to verify SMTP configuration.
    
    Use this to test that your local mail server is working correctly.
    """
    from app.services.email_notification_service import email_notification_service
    from app.config import settings
    
    # Create a test alert
    test_alert = {
        'id': 0,
        'name': 'Test Alert',
        'description': 'This is a test alert to verify email notifications are working.',
        'category': 'data_quality',
        'severity': 'low'
    }
    
    # Create test anomalies
    test_anomalies = [
        {'timestamp': datetime.now().isoformat(), 'count': 42, 'anomaly_type': 'test_spike'},
        {'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(), 'count': 35, 'anomaly_type': 'test_spike'}
    ]
    
    # Send test email
    success = email_notification_service.send_alert_notification(
        test_alert, 
        test_anomalies,
        recipients=[recipient]
    )
    
    return {
        'success': success,
        'recipient': recipient,
        'smtp_host': settings.smtp_host,
        'smtp_port': settings.smtp_port,
        'message': 'Test email sent successfully! Check your inbox (or local mail server UI).' if success else 'Failed to send email. Check server logs.'
    }


@router.post("/trigger-alert-check")
def trigger_alert_check(
    sync: bool = Query(True, description="Run synchronously (blocking) for debugging")
):
    """
    Manually trigger an immediate check of all enabled alerts.
    
    This will evaluate all alerts and send email notifications for any that trigger.
    Useful for testing without waiting for the scheduler interval.
    """
    print("[TRIGGER] Manual alert check triggered via API")
    from app.services.scheduler_service import scheduler_service
    
    if sync:
        # Run synchronously for debugging
        print("[TRIGGER] Running alert check SYNCHRONOUSLY...")
        scheduler_service._check_unified_alerts()
        print("[TRIGGER] Alert check COMPLETE")
        return {
            'message': 'Alert check completed synchronously.',
            'status': 'completed'
        }
    else:
        scheduler_service.trigger_unified_alerts_now()
        print("[TRIGGER] Alert check started in background thread")
        return {
            'message': 'Alert check triggered. Check server logs and mail inbox for results.',
            'status': 'running'
        }


@router.get("/scheduler-status")
def get_scheduler_status():
    """Get the current status of the alert scheduler."""
    from app.services.scheduler_service import scheduler_service
    from app.config import settings
    
    return {
        'enabled': settings.enable_scheduler,
        'check_interval_minutes': settings.alert_check_interval_minutes,
        'smtp_configured': settings.smtp_configured,
        'smtp_host': settings.smtp_host,
        'smtp_port': settings.smtp_port,
        'alert_recipients': settings.alert_recipients_list,
        'jobs': scheduler_service.get_jobs()
    }


@router.get("/alert-history")
def get_alert_history(
    alert_type: Optional[str] = Query(None, description="Filter by alert type: data_quality, entity_type, smart_ai"),
    alert_id: Optional[str] = Query(None, description="Filter by specific alert ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get history of triggered alerts.
    
    Returns past alert triggers with details about what was detected.
    """
    from app.models.unified_alert import (
        DataQualityAlertHistory, EntityTypeAlertHistory, SmartAIAlertHistory,
        DataQualityAlert, EntityTypeAlert, SmartAIAlert
    )
    
    history = []
    
    # Get Smart AI alert history
    if not alert_type or alert_type == 'smart_ai':
        query = db.query(SmartAIAlertHistory).join(SmartAIAlert)
        if alert_id:
            query = query.filter(SmartAIAlertHistory.alert_id == alert_id)
        smart_ai_history = query.order_by(SmartAIAlertHistory.triggered_at.desc()).limit(limit).all()
        
        for h in smart_ai_history:
            history.append({
                'id': h.id,
                'alert_id': h.alert_id,
                'alert_name': h.alert.name if h.alert else 'Unknown',
                'alert_type': 'smart_ai',
                'triggered_at': h.triggered_at.isoformat() if h.triggered_at else None,
                'anomaly_detected': h.anomaly_detected,
                'trigger_reason': h.trigger_reason,
                'details': h.anomaly_details
            })
    
    # Get Entity Type alert history
    if not alert_type or alert_type == 'entity_type':
        query = db.query(EntityTypeAlertHistory).join(EntityTypeAlert)
        if alert_id:
            query = query.filter(EntityTypeAlertHistory.alert_id == alert_id)
        entity_history = query.order_by(EntityTypeAlertHistory.triggered_at.desc()).limit(limit).all()
        
        for h in entity_history:
            history.append({
                'id': h.id,
                'alert_id': h.alert_id,
                'alert_name': h.alert.name if h.alert else 'Unknown',
                'alert_type': 'entity_type',
                'triggered_at': h.triggered_at.isoformat() if h.triggered_at else None,
                'anomaly_detected': h.is_anomaly,
                'trigger_reason': h.trigger_reason,
                'details': {
                    'email_count': h.email_count,
                    'anomaly_score': h.anomaly_score
                }
            })
    
    # Get Data Quality alert history  
    if not alert_type or alert_type == 'data_quality':
        query = db.query(DataQualityAlertHistory).join(DataQualityAlert)
        if alert_id:
            query = query.filter(DataQualityAlertHistory.alert_id == alert_id)
        dq_history = query.order_by(DataQualityAlertHistory.triggered_at.desc()).limit(limit).all()
        
        for h in dq_history:
            history.append({
                'id': h.id,
                'alert_id': h.alert_id,
                'alert_name': h.alert.name if h.alert else 'Unknown',
                'alert_type': 'data_quality',
                'triggered_at': h.triggered_at.isoformat() if h.triggered_at else None,
                'anomaly_detected': h.is_anomaly,
                'trigger_reason': h.trigger_reason,
                'details': {
                    'quality_score': h.quality_score,
                    'anomaly_score': h.anomaly_score
                }
            })
    
    # Sort by triggered_at descending
    history.sort(key=lambda x: x['triggered_at'] or '', reverse=True)
    
    return {
        'history': history[:limit],
        'total': len(history)
    }
