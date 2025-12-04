"""Email API endpoints."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import json
import csv
import io

from app.api.deps import get_db
from app.services.email_service import EmailService
from app.schemas.email import (
    EmailCreate, EmailResponse, EmailDetailResponse,
    EmailListResponse, EmailFilters
)

router = APIRouter()


@router.get("", response_model=EmailListResponse)
def list_emails(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sender: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_value: Optional[str] = None,
    has_alert: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List emails with pagination and filters.
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **sort_by**: Sort field (date, sender)
    - **sort_order**: asc or desc
    - **date_from**: Filter emails from this date
    - **date_to**: Filter emails until this date
    - **sender**: Filter by sender email
    - **entity_type**: Filter by entity type (PERSON, ORG, etc.)
    - **entity_value**: Filter by entity value
    - **has_alert**: Filter emails with/without alerts
    """
    filters = EmailFilters(
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        date_from=date_from,
        date_to=date_to,
        sender=sender,
        entity_type=entity_type,
        entity_value=entity_value,
        has_alert=has_alert
    )
    
    service = EmailService(db)
    emails, total = service.list_emails(filters)
    
    return EmailListResponse(
        total=total,
        page=page,
        limit=limit,
        emails=emails
    )


@router.get("/{email_id}", response_model=EmailDetailResponse)
def get_email(email_id: str, db: Session = Depends(get_db)):
    """
    Get a single email with all details including:
    - Email content
    - Extracted entities with positions
    - HTML body with highlighted entities
    - Triggered alerts
    - Similar emails
    """
    service = EmailService(db)
    email = service.get_email_detail(email_id)
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return email


@router.post("", response_model=EmailResponse)
def create_email(email_data: EmailCreate, db: Session = Depends(get_db)):
    """
    Create a new email with NER processing.
    
    The email will be:
    1. Stored in the database
    2. Processed for named entities
    3. Embedded for semantic search
    4. Evaluated against alert rules
    """
    service = EmailService(db)
    email = service.create_email(email_data)
    
    # Convert to response format
    return EmailResponse(
        id=email.id,
        subject=email.subject,
        sender=email.sender,
        recipients=json.loads(email.recipients) if email.recipients else [],
        date=email.date,
        preview=email.body[:200] if email.body else None,
        entity_counts={},
        alert_count=0
    )


@router.post("/upload")
async def upload_emails(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload emails from a CSV or JSON file.
    
    CSV should have columns: subject, sender, recipients, date, body
    JSON should be an array of email objects.
    """
    content = await file.read()
    content_str = content.decode("utf-8")
    
    service = EmailService(db)
    created_count = 0
    errors = []
    
    try:
        if file.filename.endswith(".json"):
            emails_data = json.loads(content_str)
            for i, email_dict in enumerate(emails_data):
                try:
                    email_create = EmailCreate(**email_dict)
                    service.create_email(email_create)
                    created_count += 1
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
        
        elif file.filename.endswith(".csv"):
            reader = csv.DictReader(io.StringIO(content_str))
            for i, row in enumerate(reader):
                try:
                    # Parse recipients if comma-separated
                    recipients = []
                    if row.get("recipients"):
                        recipients = [r.strip() for r in row["recipients"].split(",")]
                    
                    email_create = EmailCreate(
                        subject=row.get("subject"),
                        sender=row.get("sender"),
                        recipients=recipients,
                        date=datetime.fromisoformat(row["date"]) if row.get("date") else None,
                        body=row.get("body")
                    )
                    service.create_email(email_create)
                    created_count += 1
                except Exception as e:
                    errors.append(f"Row {i}: {str(e)}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use .json or .csv"
            )
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    return {
        "created": created_count,
        "errors": errors[:10] if errors else []  # Limit error messages
    }


@router.delete("/{email_id}")
def delete_email(email_id: str, db: Session = Depends(get_db)):
    """Delete an email and its associated entities and alerts."""
    service = EmailService(db)
    success = service.delete_email(email_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {"message": "Email deleted successfully"}

