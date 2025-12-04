"""Alert API endpoints."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db
from app.services.alert_service import AlertService
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse, AlertListResponse, AlertUpdate, AlertFilters
)

router = APIRouter()


# ============ Alert Rules ============

@router.get("/rules")
def list_rules(
    enabled_only: bool = Query(False, description="Only return enabled rules"),
    db: Session = Depends(get_db)
):
    """List all alert rules."""
    service = AlertService(db)
    rules = service.list_rules(enabled_only=enabled_only)
    
    return {
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "conditions": json.loads(rule.conditions),
                "created_at": rule.created_at,
                "updated_at": rule.updated_at
            }
            for rule in rules
        ]
    }


@router.post("/rules", response_model=AlertRuleResponse)
def create_rule(rule_data: AlertRuleCreate, db: Session = Depends(get_db)):
    """
    Create a new alert rule.
    
    Rule condition types:
    - **entity_threshold**: Trigger when entity value exceeds threshold (e.g., MONEY > $1M)
    - **entity_contains**: Trigger when entity contains specific values (e.g., ORG contains "SEC")
    - **keyword_entity**: Trigger when keywords appear with entities
    - **co_occurrence**: Trigger when two entity types appear together
    - **entity_count**: Trigger when entity count exceeds threshold
    - **specific_entity**: Trigger when specific entities are mentioned
    """
    service = AlertService(db)
    
    try:
        rule = service.create_rule(rule_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        severity=rule.severity,
        enabled=rule.enabled,
        conditions=json.loads(rule.conditions),
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    """Get a specific alert rule."""
    service = AlertService(db)
    rule = service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "conditions": json.loads(rule.conditions),
        "created_at": rule.created_at,
        "updated_at": rule.updated_at
    }


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_rule(
    rule_id: str,
    update_data: AlertRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert rule."""
    service = AlertService(db)
    rule = service.update_rule(rule_id, update_data)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        severity=rule.severity,
        enabled=rule.enabled,
        conditions=json.loads(rule.conditions),
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete an alert rule and all associated alerts."""
    service = AlertService(db)
    success = service.delete_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted successfully"}


@router.post("/rules/{rule_id}/test")
def test_rule(
    rule_id: str,
    sample_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Test an alert rule against sample emails.
    
    Returns how many emails would trigger the rule.
    """
    service = AlertService(db)
    rule = service.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Get sample emails and evaluate
    from app.models import Email
    emails = db.query(Email).limit(sample_size).all()
    
    matches = []
    for email in emails:
        conditions = json.loads(rule.conditions)
        email_matches = service._evaluate_rule(email, conditions)
        if email_matches:
            matches.append({
                "email_id": email.id,
                "subject": email.subject,
                "matches": email_matches
            })
    
    return {
        "rule_id": rule_id,
        "rule_name": rule.name,
        "sample_size": sample_size,
        "match_count": len(matches),
        "matches": matches[:10]  # Limit response size
    }


# ============ Alerts ============

@router.get("", response_model=AlertListResponse)
def list_alerts(
    status: Optional[str] = Query(None, pattern="^(active|acknowledged|dismissed)$"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    rule_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List triggered alerts with filters.
    
    - **status**: Filter by alert status
    - **severity**: Filter by severity level
    - **rule_id**: Filter by rule ID
    - **date_from**: Filter alerts triggered after this date
    """
    filters = AlertFilters(
        status=status,
        severity=severity,
        rule_id=rule_id,
        date_from=date_from,
        limit=limit
    )
    
    service = AlertService(db)
    alerts, total = service.list_alerts(filters)
    
    return AlertListResponse(total=total, alerts=alerts)


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific alert with details."""
    service = AlertService(db)
    alert = service.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "id": alert.id,
        "rule_id": alert.rule_id,
        "rule_name": alert.rule.name if alert.rule else None,
        "email_id": alert.email_id,
        "email_subject": alert.email.subject if alert.email else None,
        "severity": alert.severity,
        "status": alert.status,
        "matched_text": alert.matched_text,
        "context": alert.context,
        "triggered_at": alert.triggered_at
    }


@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    db: Session = Depends(get_db)
):
    """
    Update alert status.
    
    Valid statuses: active, acknowledged, dismissed
    """
    service = AlertService(db)
    alert = service.update_alert_status(alert_id, update_data.status)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        rule_id=alert.rule_id,
        rule_name=alert.rule.name if alert.rule else "Unknown",
        severity=alert.severity,
        status=alert.status,
        triggered_at=alert.triggered_at,
        email_id=alert.email_id,
        email_subject=alert.email.subject if alert.email else None,
        matched_entities=[],
        context=alert.context
    )

