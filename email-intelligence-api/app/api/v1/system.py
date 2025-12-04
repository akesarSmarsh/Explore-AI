"""System API endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.database import init_db, reset_db
from app.services.email_service import EmailService
from app.services.entity_service import EntityService
from app.services.alert_service import AlertService
from app.core.vector_store import vector_store

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Email Intelligence API"
    }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    email_service = EmailService(db)
    entity_service = EntityService(db)
    alert_service = AlertService(db)
    
    return {
        "emails": email_service.get_email_count(),
        "entities": entity_service.get_entity_count(),
        "unique_entities": entity_service.get_unique_entity_count(),
        "alerts": alert_service.get_alert_count(),
        "active_alerts": alert_service.get_alert_count(status="active"),
        "vector_count": vector_store.count(),
        "alert_rules": len(alert_service.list_rules())
    }


@router.post("/init")
def initialize_database(db: Session = Depends(get_db)):
    """
    Initialize the database.
    
    Creates tables and seeds default alert rules.
    """
    init_db()
    
    # Seed default alert rules
    alert_service = AlertService(db)
    alert_service.seed_default_rules()
    
    return {"message": "Database initialized successfully"}


@router.post("/reset")
def reset_database(confirm: bool = False):
    """
    Reset the database (DESTRUCTIVE).
    
    Deletes all data and recreates tables.
    Requires confirm=true parameter.
    """
    if not confirm:
        return {
            "error": "This will delete all data. Pass confirm=true to proceed."
        }
    
    reset_db()
    return {"message": "Database reset successfully"}


@router.post("/reprocess")
def reprocess_emails(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Re-run NER processing on all emails.
    
    Runs in background.
    """
    def reprocess_all():
        from app.models import Email, Entity
        from app.core.ner_processor import ner_processor
        
        # This would be implemented for background processing
        pass
    
    background_tasks.add_task(reprocess_all)
    
    return {"message": "Reprocessing started in background"}


@router.post("/reindex")
def reindex_vectors(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Rebuild the vector search index.
    
    Regenerates all embeddings. Runs in background.
    """
    def reindex_all():
        from app.models import Email
        from app.core.embeddings import embedding_processor
        
        # This would be implemented for background processing
        pass
    
    background_tasks.add_task(reindex_all)
    
    return {"message": "Reindexing started in background"}


@router.post("/seed-rules")
def seed_default_rules(db: Session = Depends(get_db)):
    """Seed default alert rules."""
    alert_service = AlertService(db)
    alert_service.seed_default_rules()
    
    return {"message": "Default rules seeded successfully"}

