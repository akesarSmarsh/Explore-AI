"""NER Analytics Service for word cloud and visualization data."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_, or_, extract

from app.models import Email, Entity


class NERAnalyticsService:
    """Service for NER analytics and visualization data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_wordcloud_data(
        self,
        entity_types: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sender: Optional[str] = None,
        limit: int = 100,
        min_count: int = 1
    ) -> Dict[str, Any]:
        """
        Get word cloud data with entity frequencies.
        
        Args:
            entity_types: List of entity types to include
            date_from: Start date filter
            date_to: End date filter
            sender: Sender email filter
            limit: Maximum number of entities
            min_count: Minimum occurrence count
            
        Returns:
            Word cloud data with entities, counts, and weights
        """
        # Build query
        query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label("count")
        ).join(Email, Entity.email_id == Email.id)
        
        # Apply filters
        if entity_types:
            query = query.filter(Entity.type.in_(entity_types))
        
        if date_from:
            query = query.filter(Email.date >= date_from)
        
        if date_to:
            query = query.filter(Email.date <= date_to)
        
        if sender:
            query = query.filter(Email.sender.ilike(f"%{sender}%"))
        
        # Group and filter by count
        query = query.group_by(Entity.text, Entity.type)
        query = query.having(func.count(Entity.id) >= min_count)
        query = query.order_by(func.count(Entity.id).desc())
        query = query.limit(limit)
        
        results = query.all()
        
        # Calculate weights (normalized 0-1)
        max_count = results[0].count if results else 1
        
        entities = []
        for row in results:
            weight = row.count / max_count if max_count > 0 else 0
            entities.append({
                "text": row.text,
                "type": row.type,
                "count": row.count,
                "weight": round(weight, 4)
            })
        
        # Get total unique entities
        total_query = self.db.query(func.count(distinct(Entity.text)))
        if entity_types:
            total_query = total_query.filter(Entity.type.in_(entity_types))
        total_entities = total_query.scalar() or 0
        
        return {
            "entities": entities,
            "total_entities": total_entities,
            "max_count": max_count,
            "filters_applied": {
                "entity_types": entity_types,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "sender": sender,
                "limit": limit,
                "min_count": min_count
            }
        }
    
    def get_entity_breakdown(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get entity breakdown by type.
        
        Returns:
            Breakdown statistics by entity type
        """
        query = self.db.query(
            Entity.type,
            func.count(Entity.id).label("count"),
            func.count(distinct(Entity.text)).label("unique_count")
        ).join(Email, Entity.email_id == Email.id)
        
        # Apply filters
        if date_from:
            query = query.filter(Email.date >= date_from)
        if date_to:
            query = query.filter(Email.date <= date_to)
        if sender:
            query = query.filter(Email.sender.ilike(f"%{sender}%"))
        
        query = query.group_by(Entity.type)
        query = query.order_by(func.count(Entity.id).desc())
        
        results = query.all()
        
        # Calculate totals and percentages
        total_count = sum(r.count for r in results)
        total_unique = sum(r.unique_count for r in results)
        
        types = []
        for row in results:
            percentage = (row.count / total_count * 100) if total_count > 0 else 0
            types.append({
                "type": row.type,
                "count": row.count,
                "unique_count": row.unique_count,
                "percentage": round(percentage, 2)
            })
        
        return {
            "types": types,
            "total_entities": total_count,
            "total_unique": total_unique
        }
    
    def get_trending_entities(
        self,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        granularity: str = "day",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Get trending entities over time.
        
        Args:
            entity_type: Filter by entity type
            entity_value: Filter by specific entity text
            granularity: day, week, or month
            date_from: Start date
            date_to: End date
            limit: Maximum data points
            
        Returns:
            Timeline data with entity counts
        """
        query = self.db.query(
            Email.date,
            func.count(Entity.id).label("count")
        ).join(Entity, Entity.email_id == Email.id)
        
        # Apply filters
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text.ilike(f"%{entity_value}%"))
        if date_from:
            query = query.filter(Email.date >= date_from)
        if date_to:
            query = query.filter(Email.date <= date_to)
        
        # Filter out null dates
        query = query.filter(Email.date.isnot(None))
        
        # Group by time period
        if granularity == "day":
            query = query.group_by(func.date(Email.date))
        elif granularity == "week":
            query = query.group_by(
                extract("year", Email.date),
                extract("week", Email.date)
            )
        else:  # month
            query = query.group_by(
                extract("year", Email.date),
                extract("month", Email.date)
            )
        
        query = query.order_by(Email.date.desc())
        query = query.limit(limit)
        
        results = query.all()
        
        # Format timeline
        timeline_data = defaultdict(int)
        for row in results:
            if row.date:
                if granularity == "day":
                    key = row.date.strftime("%Y-%m-%d")
                elif granularity == "week":
                    key = row.date.strftime("%Y-W%W")
                else:
                    key = row.date.strftime("%Y-%m")
                timeline_data[key] += row.count
        
        # Sort and format
        timeline = [
            {"date": date_str, "count": count, "entities": []}
            for date_str, count in sorted(timeline_data.items())
        ]
        
        return {
            "timeline": timeline,
            "entity_type": entity_type,
            "entity_value": entity_value,
            "granularity": granularity
        }
    
    def get_top_entities(
        self,
        entity_types: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sender: Optional[str] = None,
        limit: int = 50,
        min_count: int = 1
    ) -> Dict[str, Any]:
        """
        Get top entities with detailed statistics.
        
        Returns:
            Top entities with counts, email counts, and date ranges
        """
        query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label("count"),
            func.count(distinct(Entity.email_id)).label("email_count"),
            func.min(Email.date).label("first_seen"),
            func.max(Email.date).label("last_seen")
        ).join(Email, Entity.email_id == Email.id)
        
        # Apply filters
        if entity_types:
            query = query.filter(Entity.type.in_(entity_types))
        if date_from:
            query = query.filter(Email.date >= date_from)
        if date_to:
            query = query.filter(Email.date <= date_to)
        if sender:
            query = query.filter(Email.sender.ilike(f"%{sender}%"))
        
        query = query.group_by(Entity.text, Entity.type)
        query = query.having(func.count(Entity.id) >= min_count)
        query = query.order_by(func.count(Entity.id).desc())
        query = query.limit(limit)
        
        results = query.all()
        
        entities = []
        for row in results:
            entities.append({
                "text": row.text,
                "type": row.type,
                "count": row.count,
                "email_count": row.email_count,
                "first_seen": row.first_seen.date() if row.first_seen else None,
                "last_seen": row.last_seen.date() if row.last_seen else None,
                "trend": None  # Could calculate trend based on recent vs historical
            })
        
        return {
            "entities": entities,
            "total": len(entities),
            "filters_applied": {
                "entity_types": entity_types,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "sender": sender,
                "limit": limit,
                "min_count": min_count
            }
        }
    
    def get_emails_by_entity(
        self,
        entity_text: str,
        entity_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get emails containing a specific entity.
        
        Args:
            entity_text: The entity text to search for
            entity_type: Optional entity type filter
            page: Page number (1-indexed)
            limit: Number of results per page
            
        Returns:
            Dict with emails list and pagination info
        """
        # Find all email IDs containing this entity
        entity_query = self.db.query(Entity.email_id).filter(
            Entity.text.ilike(f"%{entity_text}%")
        )
        
        if entity_type:
            entity_query = entity_query.filter(Entity.type == entity_type)
        
        # Get distinct email IDs
        email_ids = [e[0] for e in entity_query.distinct().all()]
        
        if not email_ids:
            return {
                "entity_text": entity_text,
                "entity_type": entity_type,
                "total": 0,
                "page": page,
                "limit": limit,
                "total_pages": 0,
                "emails": []
            }
        
        # Get total count
        total = len(email_ids)
        total_pages = (total + limit - 1) // limit
        
        # Get emails with pagination
        offset = (page - 1) * limit
        emails_query = self.db.query(Email).filter(
            Email.id.in_(email_ids)
        ).order_by(Email.date.desc())
        
        emails = emails_query.offset(offset).limit(limit).all()
        
        # Format email results
        email_results = []
        for email in emails:
            # Get entities for this email that match the search
            matching_entities = self.db.query(Entity).filter(
                Entity.email_id == email.id,
                Entity.text.ilike(f"%{entity_text}%")
            )
            if entity_type:
                matching_entities = matching_entities.filter(Entity.type == entity_type)
            
            matching_entities = matching_entities.all()
            
            email_results.append({
                "id": email.id,
                "subject": email.subject,
                "sender": email.sender,
                "date": email.date.isoformat() if email.date else None,
                "preview": email.body[:200] if email.body else None,
                "matched_entities": [
                    {
                        "text": e.text,
                        "type": e.type,
                        "sentence": e.sentence
                    }
                    for e in matching_entities[:5]  # Limit to 5 matched entities
                ],
                "total_matched": len(matching_entities)
            })
        
        return {
            "entity_text": entity_text,
            "entity_type": entity_type,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "emails": email_results
        }
    
    def get_entity_stats_for_baseline(
        self,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Get entity statistics for anomaly detection baseline.
        
        Args:
            entity_type: Entity type to analyze
            entity_value: Specific entity to analyze
            period_days: Number of days for baseline
            
        Returns:
            Statistics including mean, std deviation, etc.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get daily counts
        query = self.db.query(
            func.date(Email.date).label("day"),
            func.count(Entity.id).label("count")
        ).join(Entity, Entity.email_id == Email.id)
        
        query = query.filter(Email.date >= start_date)
        query = query.filter(Email.date <= end_date)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text == entity_value)
        
        query = query.group_by(func.date(Email.date))
        
        results = query.all()
        
        counts = [r.count for r in results]
        
        if not counts:
            return {
                "mean": 0,
                "std_dev": 0,
                "min": 0,
                "max": 0,
                "total": 0,
                "days": 0
            }
        
        import statistics
        mean = statistics.mean(counts)
        std_dev = statistics.stdev(counts) if len(counts) > 1 else 0
        
        return {
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "min": min(counts),
            "max": max(counts),
            "total": sum(counts),
            "days": len(counts)
        }








