"""Smarsh Alerts API endpoints - Clean REST API for alert management."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.smarsh_alert_service import SmarshAlertService
from app.schemas.smarsh_alert import (
    SmarshAlertCreate, SmarshAlertUpdate, SmarshAlertResponse,
    SmarshAlertListResponse, EvaluationResult, FormOptionsResponse,
    AlertStatsResponse
)

router = APIRouter()


# ============ Form Options ============

@router.get("/options", response_model=FormOptionsResponse)
def get_form_options():
    """
    Get available options for building alert creation forms.
    
    Returns all dropdown options including:
    - Alert types (static, smart)
    - Metric types (email_volume, unique_senders, entity_mentions, keyword_matches)
    - Entity types
    - Operators
    - Anomaly detection algorithms
    - Window units
    - Severity levels
    """
    return FormOptionsResponse()


# ============ Statistics ============

@router.get("/stats", response_model=AlertStatsResponse)
def get_alert_stats(db: Session = Depends(get_db)):
    """
    Get alert statistics for dashboard.
    
    Returns:
    - Total alerts count
    - Enabled alerts count
    - Alerts triggered in last 24 hours
    - Breakdown by severity
    """
    service = SmarshAlertService(db)
    stats = service.get_alert_stats()
    return AlertStatsResponse(**stats)


# ============ CRUD Operations ============

@router.get("", response_model=SmarshAlertListResponse)
def list_alerts(
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type (static/smart)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all Smarsh alerts.
    
    Supports filtering by:
    - enabled_only: Only return active alerts
    - alert_type: Filter by 'static' or 'smart'
    """
    service = SmarshAlertService(db)
    alerts, total = service.list(enabled_only=enabled_only, alert_type=alert_type, limit=limit)
    
    return SmarshAlertListResponse(
        total=total,
        alerts=[SmarshAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("", response_model=SmarshAlertResponse)
def create_alert(data: SmarshAlertCreate, db: Session = Depends(get_db)):
    """
    Create a new Smarsh alert.
    
    ## Alert Types
    
    ### Static Alerts
    Threshold-based alerts that trigger when a metric exceeds or falls below a fixed value.
    
    ```json
    {
      "name": "High Email Volume",
      "alert_type": "static",
      "metric": {"metric_type": "email_volume"},
      "threshold": {"operator": "greater_than", "value": 100},
      "time_window": {"window_size": 1, "window_unit": "days"},
      "severity": "high"
    }
    ```
    
    ### Smart Alerts (Anomaly Detection)
    AI-powered alerts using statistical analysis (Z-score, EWMA, or % change).
    
    ```json
    {
      "name": "PERSON Mention Anomaly",
      "alert_type": "smart",
      "metric": {"metric_type": "entity_mentions", "entity_type": "PERSON"},
      "anomaly": {"algorithm": "zscore", "zscore_threshold": 2.5},
      "time_window": {"window_size": 1, "window_unit": "days", "baseline_days": 7},
      "severity": "critical"
    }
    ```
    
    ## Metrics
    
    - **email_volume**: Count of emails in time window
    - **unique_senders**: Count of unique email senders
    - **entity_mentions**: Count of entity mentions (filter by type/value)
    - **keyword_matches**: Count of keyword occurrences
    
    ## Anti-Spam Controls
    
    Configure cooldown to prevent alert storms:
    - cooldown_minutes: Time before re-alerting
    - max_alerts_per_day: Daily limit
    - consecutive_anomalies: Require N anomalies before triggering
    """
    service = SmarshAlertService(db)
    
    existing = service.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create(data)
    return SmarshAlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=SmarshAlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific alert by ID."""
    service = SmarshAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SmarshAlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=SmarshAlertResponse)
def update_alert(alert_id: str, data: SmarshAlertUpdate, db: Session = Depends(get_db)):
    """
    Update an existing alert.
    
    Only provided fields will be updated. All fields are optional.
    """
    service = SmarshAlertService(db)
    alert = service.update(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return SmarshAlertResponse.model_validate(alert)


@router.delete("/{alert_id}")
def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete an alert and all its history."""
    service = SmarshAlertService(db)
    success = service.delete(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted successfully", "alert_id": alert_id}


@router.patch("/{alert_id}/toggle")
def toggle_alert(alert_id: str, db: Session = Depends(get_db)):
    """Toggle an alert's enabled status."""
    service = SmarshAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.enabled = not alert.enabled
    db.commit()
    db.refresh(alert)
    
    return {
        "alert_id": alert_id,
        "enabled": alert.enabled,
        "message": f"Alert {'enabled' if alert.enabled else 'disabled'}"
    }


# ============ Alert Evaluation ============

@router.post("/{alert_id}/evaluate", response_model=EvaluationResult)
def evaluate_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Manually evaluate a specific alert.
    
    Returns detailed evaluation result including:
    - Whether the alert triggered
    - Current metric value vs baseline/threshold
    - Z-score (for smart alerts)
    - Percentage change
    - Time series data (last 7 days)
    - Top contributors (entities/senders causing the alert)
    - Cooldown status
    """
    service = SmarshAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    result = service.evaluate(alert)
    return EvaluationResult(**result)


@router.post("/evaluate-all")
def evaluate_all_alerts(db: Session = Depends(get_db)):
    """
    Evaluate all enabled alerts.
    
    Returns list of alerts that triggered.
    """
    service = SmarshAlertService(db)
    triggered = service.evaluate_all()
    
    return {
        "evaluated": True,
        "triggered_count": len(triggered),
        "triggered_alerts": triggered
    }


# ============ Alert History ============

@router.get("/triggered/all")
def get_all_triggered(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get all recently triggered alerts across all alert definitions.
    
    Returns trigger history with:
    - Alert name and severity
    - Trigger timestamp
    - Metric values at trigger time
    - Trigger reason
    """
    service = SmarshAlertService(db)
    triggered = service.get_triggered_alerts(limit=limit)
    
    return {
        "total": len(triggered),
        "triggered": triggered
    }


@router.get("/{alert_id}/history")
def get_alert_history(
    alert_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get trigger history for a specific alert.
    
    Returns chronological list of when this alert triggered,
    with metric values and trigger reasons.
    """
    service = SmarshAlertService(db)
    
    alert = service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    history, total = service.get_history(alert_id=alert_id, limit=limit)
    
    return {
        "alert_id": alert_id,
        "alert_name": alert.name,
        "total": total,
        "history": [
            {
                "id": h.id,
                "triggered_at": h.triggered_at.isoformat(),
                "metric_value": h.metric_value,
                "baseline_value": h.baseline_value,
                "zscore": h.zscore,
                "percentage_change": h.percentage_change,
                "trigger_reason": h.trigger_reason,
                "top_contributors": h.top_contributors,
                "notification_sent": h.notification_sent,
                "notification_status": h.notification_status
            }
            for h in history
        ]
    }


@router.delete("/{alert_id}/history")
def clear_alert_history(alert_id: str, db: Session = Depends(get_db)):
    """Clear all trigger history for a specific alert."""
    service = SmarshAlertService(db)
    
    alert = service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Delete all history for this alert
    from app.models.smarsh_alert import SmarshAlertHistory
    deleted = db.query(SmarshAlertHistory).filter(
        SmarshAlertHistory.alert_id == alert_id
    ).delete()
    
    # Reset trigger count
    alert.trigger_count = 0
    alert.alerts_today = 0
    alert.consecutive_anomaly_count = 0
    db.commit()
    
    return {
        "alert_id": alert_id,
        "deleted_count": deleted,
        "message": "Alert history cleared"
    }
