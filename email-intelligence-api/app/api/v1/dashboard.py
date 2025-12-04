"""Dashboard API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService
from app.services.ner_analytics_service import NERAnalyticsService
from app.services.smart_alert_service import SmartAlertService

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Get quick summary statistics for the dashboard header.
    
    Returns a consolidated view of:
    - Email counts
    - Entity statistics
    - Alert overview
    - Recent activity
    """
    analytics = AnalyticsService(db)
    ner_analytics = NERAnalyticsService(db)
    smart_alert_service = SmartAlertService(db)
    
    # Get overview stats
    overview = analytics.get_overview()
    
    # Get top entities for quick view
    top_entities = ner_analytics.get_top_entities(limit=5)
    
    # Get entity type breakdown
    breakdown = ner_analytics.get_entity_breakdown()
    
    # Get smart alert stats
    alerts, total_alerts = smart_alert_service.list(enabled_only=True, limit=10)
    triggered = smart_alert_service.get_triggered_alerts(limit=5)
    
    return {
        "overview": {
            "total_emails": overview.total_emails,
            "total_entities": overview.total_entities,
            "unique_entities": overview.unique_entities,
            "total_alerts": overview.total_alerts,
            "active_alerts": overview.active_alerts,
            "date_range": {
                "from": overview.date_range.from_date,
                "to": overview.date_range.to_date
            }
        },
        "entity_breakdown": breakdown["types"][:6],  # Top 6 types
        "top_entities": top_entities["entities"][:5],  # Top 5 entities
        "smart_alerts": {
            "active_count": total_alerts,
            "recent_triggered": triggered[:5]
        }
    }


@router.get("/activity")
def get_recent_activity(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get recent activity feed for the dashboard.
    
    Shows recent:
    - Triggered alerts
    - New high-value entities
    - Email processing events
    """
    smart_alert_service = SmartAlertService(db)
    
    # Get recently triggered alerts
    triggered = smart_alert_service.get_triggered_alerts(limit=limit)
    
    activity = []
    for alert in triggered:
        activity.append({
            "type": "alert_triggered",
            "timestamp": alert["triggered_at"],
            "title": f"Alert: {alert['smart_alert_name']}",
            "description": alert.get("summary", "Alert was triggered"),
            "severity": alert.get("severity", "medium"),
            "link": f"/alerts/{alert['smart_alert_id']}"
        })
    
    # Sort by timestamp
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "activity": activity[:limit]
    }










