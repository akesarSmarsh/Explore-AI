"""Analytics service for dashboard statistics."""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, extract

from app.models import Email, Entity, Alert, AlertRule
from app.schemas.analytics import (
    OverviewStats, DateRange, TimelineDataPoint, TopSender,
    NetworkNode, NetworkEdge, EntityNetworkData
)


class AnalyticsService:
    """Service for analytics operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_overview(self) -> OverviewStats:
        """Get dashboard overview statistics."""
        # Email stats
        total_emails = self.db.query(func.count(Email.id)).scalar() or 0
        
        # Entity stats
        total_entities = self.db.query(func.count(Entity.id)).scalar() or 0
        unique_entities = self.db.query(func.count(distinct(Entity.text))).scalar() or 0
        
        # Alert stats
        total_alerts = self.db.query(func.count(Alert.id)).scalar() or 0
        active_alerts = self.db.query(func.count(Alert.id)).filter(
            Alert.status == "active"
        ).scalar() or 0
        
        # Date range
        min_date = self.db.query(func.min(Email.date)).scalar()
        max_date = self.db.query(func.max(Email.date)).scalar()
        
        # Entity breakdown by type
        entity_breakdown = {}
        entity_types = self.db.query(
            Entity.type,
            func.count(Entity.id)
        ).group_by(Entity.type).all()
        for entity_type, count in entity_types:
            entity_breakdown[entity_type] = count
        
        # Alert breakdown by severity
        alert_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        alert_severities = self.db.query(
            Alert.severity,
            func.count(Alert.id)
        ).group_by(Alert.severity).all()
        for severity, count in alert_severities:
            alert_breakdown[severity] = count
        
        return OverviewStats(
            total_emails=total_emails,
            total_entities=total_entities,
            unique_entities=unique_entities,
            total_alerts=total_alerts,
            active_alerts=active_alerts,
            date_range=DateRange(
                from_date=min_date.date() if min_date else None,
                to_date=max_date.date() if max_date else None
            ),
            entity_breakdown=entity_breakdown,
            alert_breakdown=alert_breakdown
        )
    
    def get_timeline(
        self,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        granularity: str = "month",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[TimelineDataPoint]:
        """Get entity mentions over time."""
        query = self.db.query(Email.date).join(Entity)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        if entity_value:
            query = query.filter(Entity.text.ilike(f"%{entity_value}%"))
        if date_from:
            query = query.filter(Email.date >= date_from)
        if date_to:
            query = query.filter(Email.date <= date_to)
        
        # Group by time period
        if granularity == "day":
            date_format = "%Y-%m-%d"
            query = query.group_by(func.date(Email.date))
        elif granularity == "week":
            date_format = "%Y-W%W"
            query = query.group_by(
                extract("year", Email.date),
                extract("week", Email.date)
            )
        else:  # month
            date_format = "%Y-%m"
            query = query.group_by(
                extract("year", Email.date),
                extract("month", Email.date)
            )
        
        # Get counts
        timeline_data = defaultdict(int)
        for row in query.all():
            if row.date:
                if granularity == "day":
                    key = row.date.strftime("%Y-%m-%d")
                elif granularity == "week":
                    key = row.date.strftime("%Y-W%W")
                else:
                    key = row.date.strftime("%Y-%m")
                timeline_data[key] += 1
        
        # Sort and format
        sorted_timeline = sorted(timeline_data.items())
        return [
            TimelineDataPoint(date=date_str, count=count)
            for date_str, count in sorted_timeline
        ]
    
    def get_top_senders(self, limit: int = 20) -> List[TopSender]:
        """Get most active email senders."""
        results = self.db.query(
            Email.sender,
            func.count(Email.id).label("email_count"),
            func.count(Entity.id).label("entity_count")
        ).outerjoin(Entity).filter(
            Email.sender.isnot(None)
        ).group_by(Email.sender).order_by(
            func.count(Email.id).desc()
        ).limit(limit).all()
        
        return [
            TopSender(
                sender=row.sender,
                email_count=row.email_count,
                entity_count=row.entity_count
            )
            for row in results
        ]
    
    def get_entity_network(
        self,
        entity_types: Optional[List[str]] = None,
        min_weight: int = 2,
        limit: int = 100
    ) -> EntityNetworkData:
        """Get entity relationship network data."""
        # Get entities, optionally filtered by type
        query = self.db.query(Entity.email_id, Entity.text, Entity.type)
        if entity_types:
            query = query.filter(Entity.type.in_(entity_types))
        
        # Group entities by email
        entities_by_email = defaultdict(list)
        entity_counts = defaultdict(lambda: {"type": None, "count": 0})
        
        for row in query.all():
            entities_by_email[row.email_id].append({
                "text": row.text,
                "type": row.type
            })
            entity_counts[row.text]["type"] = row.type
            entity_counts[row.text]["count"] += 1
        
        # Count co-occurrences (edges)
        edge_counts = defaultdict(int)
        for email_id, entities in entities_by_email.items():
            unique_entities = list({e["text"] for e in entities})
            for i, e1 in enumerate(unique_entities):
                for e2 in unique_entities[i + 1:]:
                    key = tuple(sorted([e1, e2]))
                    edge_counts[key] += 1
        
        # Filter edges by minimum weight
        edges = []
        connected_nodes = set()
        for (e1, e2), weight in sorted(edge_counts.items(), key=lambda x: -x[1])[:limit]:
            if weight >= min_weight:
                edges.append(NetworkEdge(source=e1, target=e2, weight=weight))
                connected_nodes.add(e1)
                connected_nodes.add(e2)
        
        # Create nodes for connected entities only
        nodes = []
        for entity_text in connected_nodes:
            data = entity_counts[entity_text]
            nodes.append(NetworkNode(
                id=entity_text,
                type=data["type"],
                count=data["count"]
            ))
        
        return EntityNetworkData(nodes=nodes, edges=edges)
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """Get alert statistics summary."""
        total = self.db.query(func.count(Alert.id)).scalar() or 0
        
        by_status = dict(
            self.db.query(Alert.status, func.count(Alert.id))
            .group_by(Alert.status).all()
        )
        
        by_severity = dict(
            self.db.query(Alert.severity, func.count(Alert.id))
            .group_by(Alert.severity).all()
        )
        
        by_rule = self.db.query(
            AlertRule.name,
            func.count(Alert.id)
        ).join(Alert).group_by(AlertRule.name).all()
        
        return {
            "total": total,
            "by_status": {
                "active": by_status.get("active", 0),
                "acknowledged": by_status.get("acknowledged", 0),
                "dismissed": by_status.get("dismissed", 0)
            },
            "by_severity": {
                "critical": by_severity.get("critical", 0),
                "high": by_severity.get("high", 0),
                "medium": by_severity.get("medium", 0),
                "low": by_severity.get("low", 0)
            },
            "by_rule": [{"rule": name, "count": count} for name, count in by_rule]
        }

