"""Entity service for business logic."""
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models import Entity, Email


class EntityService:
    """Service for entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_entities(
        self,
        entity_type: Optional[str] = None,
        min_count: int = 1,
        limit: int = 100,
        sort_by: str = "count"
    ) -> List[Dict[str, Any]]:
        """
        List aggregated entities with counts.
        
        Args:
            entity_type: Filter by entity type
            min_count: Minimum occurrence count
            limit: Maximum results
            sort_by: Sort field (count, text)
            
        Returns:
            List of aggregated entity data
        """
        query = self.db.query(
            Entity.text,
            Entity.type,
            func.count(Entity.id).label("count"),
            func.count(distinct(Entity.email_id)).label("email_count"),
            func.min(Email.date).label("first_seen"),
            func.max(Email.date).label("last_seen")
        ).join(Email, Entity.email_id == Email.id)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        
        query = query.group_by(Entity.text, Entity.type)
        query = query.having(func.count(Entity.id) >= min_count)
        
        if sort_by == "count":
            query = query.order_by(func.count(Entity.id).desc())
        else:
            query = query.order_by(Entity.text)
        
        query = query.limit(limit)
        
        results = []
        for row in query.all():
            results.append({
                "text": row.text,
                "type": row.type,
                "count": row.count,
                "email_count": row.email_count,
                "first_seen": row.first_seen.date() if row.first_seen else None,
                "last_seen": row.last_seen.date() if row.last_seen else None
            })
        
        return results
    
    def get_entity_types(self) -> List[Dict[str, Any]]:
        """
        Get statistics by entity type.
        
        Returns:
            List of type statistics
        """
        results = self.db.query(
            Entity.type,
            func.count(Entity.id).label("count"),
            func.count(distinct(Entity.text)).label("unique")
        ).group_by(Entity.type).all()
        
        return [
            {
                "type": row.type,
                "count": row.count,
                "unique": row.unique
            }
            for row in results
        ]
    
    def get_entities_by_type(
        self,
        entity_type: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get entities of a specific type.
        
        Args:
            entity_type: The entity type
            limit: Maximum results
            
        Returns:
            List of entities with counts
        """
        return self.list_entities(entity_type=entity_type, limit=limit)
    
    def get_co_occurrences(
        self,
        entity_type_1: Optional[str] = None,
        entity_type_2: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get entity co-occurrence data.
        
        Args:
            entity_type_1: Filter first entity type
            entity_type_2: Filter second entity type
            limit: Maximum results
            
        Returns:
            List of co-occurrence data
        """
        # Get all entities grouped by email
        query = self.db.query(Entity.email_id, Entity.text, Entity.type)
        
        if entity_type_1:
            query = query.filter(Entity.type.in_([entity_type_1, entity_type_2] if entity_type_2 else [entity_type_1]))
        
        entities_by_email = defaultdict(list)
        for row in query.all():
            entities_by_email[row.email_id].append({
                "text": row.text,
                "type": row.type
            })
        
        # Count co-occurrences
        co_occurrences = defaultdict(lambda: {"count": 0, "emails": []})
        
        for email_id, entities in entities_by_email.items():
            # Create pairs
            for i, e1 in enumerate(entities):
                for e2 in entities[i + 1:]:
                    # Skip same type pairs if we're filtering
                    if entity_type_1 and entity_type_2:
                        if not ((e1["type"] == entity_type_1 and e2["type"] == entity_type_2) or
                                (e1["type"] == entity_type_2 and e2["type"] == entity_type_1)):
                            continue
                    
                    # Create consistent key
                    if e1["text"] < e2["text"]:
                        key = (e1["text"], e1["type"], e2["text"], e2["type"])
                    else:
                        key = (e2["text"], e2["type"], e1["text"], e1["type"])
                    
                    co_occurrences[key]["count"] += 1
                    if len(co_occurrences[key]["emails"]) < 5:
                        co_occurrences[key]["emails"].append(email_id)
        
        # Sort and limit
        sorted_coocs = sorted(
            co_occurrences.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:limit]
        
        results = []
        for (text1, type1, text2, type2), data in sorted_coocs:
            results.append({
                "entity1": {"text": text1, "type": type1},
                "entity2": {"text": text2, "type": type2},
                "count": data["count"],
                "emails": data["emails"]
            })
        
        return results
    
    def get_entity_count(self) -> int:
        """Get total entity count."""
        return self.db.query(func.count(Entity.id)).scalar()
    
    def get_unique_entity_count(self) -> int:
        """Get unique entity count."""
        return self.db.query(func.count(distinct(Entity.text))).scalar()

