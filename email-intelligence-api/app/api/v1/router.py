"""Main API v1 router."""
from fastapi import APIRouter

from app.api.v1 import (
    emails, entities, search, alerts, analytics, system, 
    ner, smart_alerts, dashboard, volume_alerts, smarsh_alerts,
    unified_alerts
)

api_router = APIRouter()

api_router.include_router(emails.router, prefix="/emails", tags=["Emails"])
api_router.include_router(entities.router, prefix="/entities", tags=["Entities"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(smart_alerts.router, prefix="/smart-alerts", tags=["Smart Alerts"])
api_router.include_router(volume_alerts.router, prefix="/volume-alerts", tags=["Volume Alerts"])
api_router.include_router(smarsh_alerts.router, prefix="/smarsh-alerts", tags=["Smarsh Alerts"])
api_router.include_router(unified_alerts.router, prefix="/unified-alerts", tags=["Unified Alerts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
api_router.include_router(ner.router, prefix="/ner", tags=["NER Visualization"])
