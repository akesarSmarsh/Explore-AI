"""NER Analytics API endpoints."""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.ner_analytics_service import NERAnalyticsService
from app.core.ner_processor import ner_processor
from app.models import Email
from app.schemas.ner import (
    WordCloudResponse, BreakdownResponse, 
    TrendingResponse, TopEntitiesResponse,
    EmailsByEntityResponse
)

router = APIRouter()


@router.get("/wordcloud", response_model=WordCloudResponse)
def get_wordcloud(
    entity_types: Optional[str] = Query(
        None, 
        description="Comma-separated entity types (PERSON,ORG,MONEY)"
    ),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    limit: int = Query(100, ge=1, le=500, description="Maximum entities to return"),
    min_count: int = Query(1, ge=1, description="Minimum occurrence count"),
    db: Session = Depends(get_db)
):
    """
    Get word cloud data for entity visualization.
    
    Returns entity frequencies with normalized weights for word cloud rendering.
    
    - **entity_types**: Filter by entity type (comma-separated)
    - **date_from/date_to**: Date range filter
    - **sender**: Filter by sender email
    - **limit**: Maximum number of entities (default: 100)
    - **min_count**: Minimum occurrence threshold
    """
    # Parse entity types
    types_list = None
    if entity_types:
        types_list = [t.strip().upper() for t in entity_types.split(",")]
    
    service = NERAnalyticsService(db)
    data = service.get_wordcloud_data(
        entity_types=types_list,
        date_from=date_from,
        date_to=date_to,
        sender=sender,
        limit=limit,
        min_count=min_count
    )
    
    return WordCloudResponse(**data)


@router.get("/breakdown", response_model=BreakdownResponse)
def get_breakdown(
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    db: Session = Depends(get_db)
):
    """
    Get entity breakdown by type.
    
    Returns statistics for each entity type including:
    - Total count
    - Unique count
    - Percentage of total
    """
    service = NERAnalyticsService(db)
    data = service.get_entity_breakdown(
        date_from=date_from,
        date_to=date_to,
        sender=sender
    )
    
    return BreakdownResponse(**data)


@router.get("/trending", response_model=TrendingResponse)
def get_trending(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_value: Optional[str] = Query(None, description="Filter by specific entity"),
    granularity: str = Query("day", pattern="^(day|week|month)$", description="Time granularity"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_db)
):
    """
    Get trending entities over time.
    
    Returns timeline data showing entity mention counts over time.
    Useful for spotting trends and patterns.
    
    - **entity_type**: Filter to specific type (PERSON, ORG, etc.)
    - **entity_value**: Filter to specific entity text
    - **granularity**: day, week, or month
    """
    service = NERAnalyticsService(db)
    data = service.get_trending_entities(
        entity_type=entity_type.upper() if entity_type else None,
        entity_value=entity_value,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )
    
    return TrendingResponse(**data)


@router.get("/top-entities", response_model=TopEntitiesResponse)
def get_top_entities(
    entity_types: Optional[str] = Query(
        None,
        description="Comma-separated entity types"
    ),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    limit: int = Query(50, ge=1, le=200, description="Maximum entities"),
    min_count: int = Query(1, ge=1, description="Minimum occurrence count"),
    db: Session = Depends(get_db)
):
    """
    Get top entities with detailed statistics.
    
    Returns top entities sorted by occurrence count with:
    - Total mention count
    - Number of emails containing entity
    - First and last seen dates
    """
    # Parse entity types
    types_list = None
    if entity_types:
        types_list = [t.strip().upper() for t in entity_types.split(",")]
    
    service = NERAnalyticsService(db)
    data = service.get_top_entities(
        entity_types=types_list,
        date_from=date_from,
        date_to=date_to,
        sender=sender,
        limit=limit,
        min_count=min_count
    )
    
    return TopEntitiesResponse(**data)


@router.get("/baseline/{entity_type}")
def get_baseline_stats(
    entity_type: str,
    entity_value: Optional[str] = Query(None, description="Specific entity value"),
    period_days: int = Query(7, ge=1, le=90, description="Baseline period in days"),
    db: Session = Depends(get_db)
):
    """
    Get baseline statistics for anomaly detection.
    
    Returns mean, standard deviation, and other stats for the specified
    entity type over the given period.
    
    Useful for configuring anomaly detection thresholds.
    """
    service = NERAnalyticsService(db)
    stats = service.get_entity_stats_for_baseline(
        entity_type=entity_type.upper(),
        entity_value=entity_value,
        period_days=period_days
    )
    
    return {
        "entity_type": entity_type.upper(),
        "entity_value": entity_value,
        "period_days": period_days,
        "stats": stats
    }


@router.get("/emails-by-entity", response_model=EmailsByEntityResponse)
def get_emails_by_entity(
    entity_text: str = Query(..., min_length=1, description="Entity text to search for"),
    entity_type: Optional[str] = Query(None, description="Entity type filter (PERSON, ORG, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Get all emails containing a specific entity.
    
    Use this endpoint to find all documents/emails that mention a particular entity.
    This is useful for making word cloud entities clickable to see related emails.
    
    **Example Usage:**
    - Click on "John Smith" in word cloud → GET /api/v1/ner/emails-by-entity?entity_text=John Smith&entity_type=PERSON
    - Click on "Microsoft" in word cloud → GET /api/v1/ner/emails-by-entity?entity_text=Microsoft&entity_type=ORG
    
    **Response includes:**
    - Total count of emails containing this entity
    - Paginated list of emails with previews
    - Matched entity occurrences in each email
    
    Args:
        entity_text: The entity text to search for (required)
        entity_type: Optional filter by entity type (PERSON, ORG, GPE, MONEY, etc.)
        page: Page number for pagination (default: 1)
        limit: Number of results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of emails containing the entity
    """
    service = NERAnalyticsService(db)
    
    result = service.get_emails_by_entity(
        entity_text=entity_text,
        entity_type=entity_type.upper() if entity_type else None,
        page=page,
        limit=limit
    )
    
    return result


@router.post("/extract-phrases")
def extract_phrases(
    text: str = Query(..., min_length=10, description="Text to extract phrases from")
):
    """
    Extract noun phrases, verb phrases, and actions from text.
    
    This endpoint uses spaCy's dependency parsing to extract:
    - **Noun Phrases**: Important noun chunks (e.g., "quarterly financial report")
    - **Verb Phrases**: Verb combinations including auxiliaries and particles (e.g., "has been investigating")
    - **Actions**: Subject-verb-object triples (e.g., "team reviewed documents")
    
    **Example:**
    ```
    POST /api/v1/ner/extract-phrases?text=The team has been investigating financial irregularities in quarterly reports.
    ```
    
    **Response:**
    ```json
    {
        "noun_phrases": [{"text": "financial irregularities", "type": "NOUN_PHRASE", ...}],
        "verb_phrases": [{"text": "has been investigating", "type": "VERB_PHRASE", ...}],
        "actions": [{"text": "team investigate irregularities", "verb": "investigating", ...}]
    }
    ```
    """
    result = ner_processor.extract_phrases(text)
    return result


@router.get("/phrases/wordcloud")
def get_phrases_wordcloud(
    phrase_type: str = Query("all", description="Type: noun_phrases, verb_phrases, actions, or all"),
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    sender: Optional[str] = Query(None, description="Filter by sender email"),
    limit: int = Query(100, ge=1, le=500, description="Maximum phrases to return"),
    db: Session = Depends(get_db)
):
    """
    Get phrase word cloud data aggregated from emails.
    
    Extracts and aggregates phrases from email bodies to create word cloud data.
    
    **Phrase Types:**
    - `noun_phrases`: Noun chunks like "financial report", "quarterly earnings"
    - `verb_phrases`: Verb combinations like "has reviewed", "will investigate"
    - `actions`: Subject-verb-object patterns like "team reviewed documents"
    - `all`: All phrase types combined
    
    **Example:**
    ```
    GET /api/v1/ner/phrases/wordcloud?phrase_type=verb_phrases&limit=50
    ```
    """
    from collections import Counter
    
    # Query emails
    query = db.query(Email)
    
    if date_from:
        query = query.filter(Email.date >= date_from)
    if date_to:
        query = query.filter(Email.date <= date_to)
    if sender:
        query = query.filter(Email.sender.ilike(f"%{sender}%"))
    
    # Limit to recent emails for performance
    emails = query.order_by(Email.date.desc()).limit(500).all()
    
    # Aggregate phrases
    noun_phrase_counter = Counter()
    verb_phrase_counter = Counter()
    action_counter = Counter()
    
    for email in emails:
        if not email.body:
            continue
        
        # Extract phrases from email body (limit text size for performance)
        text = email.body[:5000] if len(email.body) > 5000 else email.body
        phrases = ner_processor.extract_phrases(text)
        
        # Count phrases
        for np in phrases["noun_phrases"]:
            noun_phrase_counter[np["text"].lower()] += 1
        
        for vp in phrases["verb_phrases"]:
            verb_phrase_counter[vp["text"].lower()] += 1
        
        for action in phrases["actions"]:
            action_counter[action["text"].lower()] += 1
    
    # Build response based on phrase_type
    def counter_to_wordcloud(counter: Counter, phrase_type: str, limit: int):
        items = counter.most_common(limit)
        if not items:
            return []
        
        max_count = items[0][1] if items else 1
        return [
            {
                "text": text,
                "type": phrase_type,
                "count": count,
                "weight": round(count / max_count, 4)
            }
            for text, count in items
        ]
    
    result = {
        "filters_applied": {
            "phrase_type": phrase_type,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "sender": sender,
            "limit": limit,
            "emails_processed": len(emails)
        }
    }
    
    if phrase_type == "noun_phrases":
        result["phrases"] = counter_to_wordcloud(noun_phrase_counter, "NOUN_PHRASE", limit)
    elif phrase_type == "verb_phrases":
        result["phrases"] = counter_to_wordcloud(verb_phrase_counter, "VERB_PHRASE", limit)
    elif phrase_type == "actions":
        result["phrases"] = counter_to_wordcloud(action_counter, "ACTION", limit)
    else:  # all
        result["noun_phrases"] = counter_to_wordcloud(noun_phrase_counter, "NOUN_PHRASE", limit // 3)
        result["verb_phrases"] = counter_to_wordcloud(verb_phrase_counter, "VERB_PHRASE", limit // 3)
        result["actions"] = counter_to_wordcloud(action_counter, "ACTION", limit // 3)
    
    return result


@router.get("/email/{email_id}/phrases")
def get_email_phrases(
    email_id: str,
    db: Session = Depends(get_db)
):
    """
    Extract all phrases from a specific email.
    
    Returns entities, noun phrases, verb phrases, and actions from the email body.
    
    **Example:**
    ```
    GET /api/v1/ner/email/abc123/phrases
    ```
    """
    from fastapi import HTTPException
    
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    if not email.body:
        return {
            "email_id": email_id,
            "subject": email.subject,
            "entities": [],
            "noun_phrases": [],
            "verb_phrases": [],
            "actions": []
        }
    
    # Extract all NER and phrases
    all_extractions = ner_processor.extract_all(email.body)
    
    return {
        "email_id": email_id,
        "subject": email.subject,
        "sender": email.sender,
        "date": email.date.isoformat() if email.date else None,
        **all_extractions
    }


@router.get("/emails-by-phrase")
def get_emails_by_phrase(
    phrase_text: str = Query(..., min_length=2, description="Phrase text to search for"),
    phrase_type: Optional[str] = Query(None, description="Phrase type (NOUN_PHRASE, VERB_PHRASE, ACTION)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Get all emails containing a specific phrase.
    
    Searches email bodies for the phrase text and returns matching emails.
    This enables clickable phrases in the word cloud.
    
    **Example Usage:**
    - Click on "quarterly report" → GET /api/v1/ner/emails-by-phrase?phrase_text=quarterly report
    - Click on "has been investigating" → GET /api/v1/ner/emails-by-phrase?phrase_text=has been investigating
    
    **Response includes:**
    - Total count of emails containing this phrase
    - Paginated list of emails with previews
    - Context snippets showing where the phrase appears
    """
    from sqlalchemy import or_
    
    # Search for phrase in email body (case-insensitive)
    search_term = f"%{phrase_text}%"
    
    query = db.query(Email).filter(
        Email.body.ilike(search_term)
    )
    
    # Get total count
    total = query.count()
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    if total == 0:
        return {
            "phrase_text": phrase_text,
            "phrase_type": phrase_type,
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "emails": []
        }
    
    # Get paginated results
    offset = (page - 1) * limit
    emails = query.order_by(Email.date.desc()).offset(offset).limit(limit).all()
    
    # Format results with context snippets
    email_results = []
    for email in emails:
        # Find context around the phrase
        context_snippet = None
        if email.body:
            body_lower = email.body.lower()
            phrase_lower = phrase_text.lower()
            pos = body_lower.find(phrase_lower)
            if pos != -1:
                # Get surrounding context
                start = max(0, pos - 50)
                end = min(len(email.body), pos + len(phrase_text) + 100)
                context_snippet = email.body[start:end]
                if start > 0:
                    context_snippet = "..." + context_snippet
                if end < len(email.body):
                    context_snippet = context_snippet + "..."
        
        # Count occurrences
        occurrence_count = 0
        if email.body:
            occurrence_count = email.body.lower().count(phrase_text.lower())
        
        email_results.append({
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,
            "date": email.date.isoformat() if email.date else None,
            "preview": email.body[:200] if email.body else None,
            "context_snippet": context_snippet,
            "occurrence_count": occurrence_count
        })
    
    return {
        "phrase_text": phrase_text,
        "phrase_type": phrase_type,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "emails": email_results
    }






