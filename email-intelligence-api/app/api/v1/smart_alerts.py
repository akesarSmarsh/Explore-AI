"""Smart Alerts API endpoints."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.smart_alert_service import SmartAlertService
from app.schemas.smart_alert import (
    SmartAlertCreate, SmartAlertUpdate, SmartAlertResponse,
    SmartAlertListResponse, AlertHistoryListResponse, AlertHistoryResponse,
    TestAlertRequest, TestAlertResponse
)

router = APIRouter()


# ============ Smart Alert CRUD ============

@router.get("", response_model=SmartAlertListResponse)
def list_smart_alerts(
    enabled_only: bool = Query(False, description="Only return enabled alerts"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    List all smart alerts.
    
    Alert types:
    - Standard: entity_threshold, entity_mention, keyword_match, co_occurrence, pattern_match
    - Anomaly: volume_spike, sudden_appearance, frequency_change
    """
    service = SmartAlertService(db)
    alerts, total = service.list(
        enabled_only=enabled_only,
        alert_type=alert_type,
        limit=limit
    )
    
    return SmartAlertListResponse(
        total=total,
        alerts=[SmartAlertResponse.model_validate(a) for a in alerts]
    )


@router.post("", response_model=SmartAlertResponse)
def create_smart_alert(
    data: SmartAlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new smart alert.
    
    ## Alert Types
    
    ### Standard Alerts
    - **entity_threshold**: Trigger when entity value exceeds threshold
    - **entity_mention**: Trigger when specific entities are mentioned
    - **keyword_match**: Trigger when keywords are detected
    - **co_occurrence**: Trigger when entity types appear together
    - **pattern_match**: Trigger when regex pattern matches
    
    ### Anomaly Detection Alerts
    - **volume_spike**: Trigger when entity mentions exceed baseline
    - **sudden_appearance**: Trigger when new entities appear
    - **frequency_change**: Trigger when mention frequency changes significantly
    
    ## Example Anomaly Alert
    ```json
    {
      "name": "PERSON volume spike",
      "alert_type": "volume_spike",
      "anomaly_config": {
        "entity_type": "PERSON",
        "monitoring_window": {"duration": 24, "unit": "hours"},
        "baseline_period": {"duration": 7, "unit": "days"},
        "threshold": {"type": "percentage", "value": 50}
      },
      "severity": "high"
    }
    ```
    """
    service = SmartAlertService(db)
    
    # Check for duplicate name
    existing = service.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Alert with this name already exists")
    
    alert = service.create(data)
    return SmartAlertResponse.model_validate(alert)


@router.get("/{alert_id}", response_model=SmartAlertResponse)
def get_smart_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific smart alert by ID."""
    service = SmartAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    return SmartAlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=SmartAlertResponse)
def update_smart_alert(
    alert_id: str,
    data: SmartAlertUpdate,
    db: Session = Depends(get_db)
):
    """Update a smart alert."""
    service = SmartAlertService(db)
    alert = service.update(alert_id, data)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    return SmartAlertResponse.model_validate(alert)


@router.delete("/{alert_id}")
def delete_smart_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete a smart alert and its history."""
    service = SmartAlertService(db)
    success = service.delete(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    return {"message": "Smart alert deleted successfully"}


# ============ Alert Evaluation ============

@router.post("/{alert_id}/evaluate")
def evaluate_alert(alert_id: str, db: Session = Depends(get_db)):
    """
    Manually evaluate a specific alert.
    
    Returns whether the alert would trigger and the matched data.
    """
    service = SmartAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    triggered, matched_data = service.evaluate(alert)
    
    return {
        "alert_id": alert_id,
        "alert_name": alert.name,
        "triggered": triggered,
        "matched_data": matched_data
    }


@router.post("/evaluate-all")
def evaluate_all_alerts(
    background_tasks: BackgroundTasks,
    run_async: bool = Query(False, description="Run in background"),
    db: Session = Depends(get_db)
):
    """
    Evaluate all enabled alerts.
    
    Can run synchronously (default) or asynchronously in background.
    """
    service = SmartAlertService(db)
    
    if run_async:
        background_tasks.add_task(service.evaluate_all)
        return {"message": "Alert evaluation started in background"}
    
    triggered = service.evaluate_all()
    
    return {
        "evaluated": True,
        "triggered_count": len(triggered),
        "triggered_alerts": triggered
    }


@router.post("/{alert_id}/test", response_model=TestAlertResponse)
def test_alert(
    alert_id: str,
    request: TestAlertRequest,
    db: Session = Depends(get_db)
):
    """
    Test an alert against sample data.
    
    Useful for validating alert configuration before enabling.
    """
    service = SmartAlertService(db)
    alert = service.get(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    # Temporarily evaluate
    triggered, matched_data = service.evaluate(alert)
    
    matches = []
    if matched_data:
        raw_matches = matched_data.get("matches", [])
        for m in raw_matches[:10]:
            matches.append({
                "email_id": m.get("email_id", ""),
                "email_subject": m.get("subject"),
                "matched_data": m
            })
    
    return TestAlertResponse(
        alert_id=alert_id,
        alert_name=alert.name,
        sample_size=request.sample_size,
        match_count=len(matches),
        matches=matches,
        would_trigger=triggered
    )


# ============ Alert History ============

@router.get("/{alert_id}/history", response_model=AlertHistoryListResponse)
def get_alert_history(
    alert_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get trigger history for a specific alert."""
    service = SmartAlertService(db)
    
    alert = service.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Smart alert not found")
    
    history, total = service.get_history(alert_id=alert_id, limit=limit)
    
    return AlertHistoryListResponse(
        total=total,
        history=[
            AlertHistoryResponse(
                id=h.id,
                smart_alert_id=h.smart_alert_id,
                smart_alert_name=alert.name,
                email_id=h.email_id,
                email_subject=h.email.subject if h.email else None,
                triggered_at=h.triggered_at,
                matched_data=h.matched_data,
                summary=h.summary,
                notification_sent=h.notification_sent,
                notification_status=h.notification_status
            )
            for h in history
        ]
    )


@router.get("/triggered/all")
def get_all_triggered_alerts(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all recently triggered alerts across all alert definitions."""
    service = SmartAlertService(db)
    triggered = service.get_triggered_alerts(limit=limit)
    
    return {
        "total": len(triggered),
        "triggered": triggered
    }










