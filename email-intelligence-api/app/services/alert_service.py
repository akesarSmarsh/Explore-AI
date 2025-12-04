"""Alert service for business logic."""
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import AlertRule, Alert, Email, Entity
from app.schemas.alert import (
    AlertRuleCreate, AlertRuleUpdate, AlertFilters,
    RuleCondition
)


class AlertService:
    """Service for alert operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ Alert Rules ============
    
    def create_rule(self, rule_data: AlertRuleCreate) -> AlertRule:
        """Create a new alert rule."""
        rule = AlertRule(
            name=rule_data.name,
            description=rule_data.description,
            severity=rule_data.severity,
            enabled=rule_data.enabled,
            conditions=json.dumps(rule_data.conditions.model_dump())
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get alert rule by ID."""
        return self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    
    def list_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """List all alert rules."""
        query = self.db.query(AlertRule)
        if enabled_only:
            query = query.filter(AlertRule.enabled == True)
        return query.order_by(AlertRule.created_at.desc()).all()
    
    def update_rule(self, rule_id: str, update_data: AlertRuleUpdate) -> Optional[AlertRule]:
        """Update an alert rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        
        if update_data.name is not None:
            rule.name = update_data.name
        if update_data.description is not None:
            rule.description = update_data.description
        if update_data.severity is not None:
            rule.severity = update_data.severity
        if update_data.enabled is not None:
            rule.enabled = update_data.enabled
        if update_data.conditions is not None:
            rule.conditions = json.dumps(update_data.conditions.model_dump())
        
        self.db.commit()
        self.db.refresh(rule)
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True
    
    # ============ Alerts ============
    
    def list_alerts(self, filters: AlertFilters) -> tuple[List[Dict[str, Any]], int]:
        """List triggered alerts with filters."""
        query = self.db.query(Alert).join(AlertRule).join(Email)
        
        if filters.status:
            query = query.filter(Alert.status == filters.status)
        if filters.severity:
            query = query.filter(Alert.severity == filters.severity)
        if filters.rule_id:
            query = query.filter(Alert.rule_id == filters.rule_id)
        if filters.date_from:
            query = query.filter(Alert.triggered_at >= filters.date_from)
        
        total = query.count()
        
        alerts = query.order_by(Alert.triggered_at.desc()).limit(filters.limit).all()
        
        results = []
        for alert in alerts:
            results.append({
                "id": alert.id,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule.name if alert.rule else "Unknown",
                "severity": alert.severity,
                "status": alert.status,
                "triggered_at": alert.triggered_at,
                "email_id": alert.email_id,
                "email_subject": alert.email.subject if alert.email else None,
                "matched_entities": [{"text": alert.matched_text, "type": ""}] if alert.matched_text else [],
                "context": alert.context
            })
        
        return results, total
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self.db.query(Alert).filter(Alert.id == alert_id).first()
    
    def update_alert_status(self, alert_id: str, status: str) -> Optional[Alert]:
        """Update alert status."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        alert.status = status
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    # ============ Alert Evaluation ============
    
    def evaluate_email(self, email: Email) -> List[Alert]:
        """
        Evaluate an email against all enabled rules.
        
        Args:
            email: The email to evaluate
            
        Returns:
            List of triggered alerts
        """
        rules = self.list_rules(enabled_only=True)
        triggered_alerts = []
        
        for rule in rules:
            conditions = json.loads(rule.conditions)
            matches = self._evaluate_rule(email, conditions)
            
            for match in matches:
                alert = Alert(
                    rule_id=rule.id,
                    email_id=email.id,
                    entity_id=match.get("entity_id"),
                    severity=rule.severity,
                    status="active",
                    matched_text=match.get("matched_text"),
                    context=match.get("context")
                )
                self.db.add(alert)
                triggered_alerts.append(alert)
        
        if triggered_alerts:
            self.db.commit()
        
        return triggered_alerts
    
    def _evaluate_rule(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate a single rule against an email."""
        rule_type = conditions.get("type")
        
        if rule_type == "entity_threshold":
            return self._eval_entity_threshold(email, conditions)
        elif rule_type == "entity_contains":
            return self._eval_entity_contains(email, conditions)
        elif rule_type == "keyword_entity":
            return self._eval_keyword_entity(email, conditions)
        elif rule_type == "co_occurrence":
            return self._eval_co_occurrence(email, conditions)
        elif rule_type == "entity_count":
            return self._eval_entity_count(email, conditions)
        elif rule_type == "specific_entity":
            return self._eval_specific_entity(email, conditions)
        
        return []
    
    def _eval_entity_threshold(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate entity threshold condition (e.g., MONEY > 1000000)."""
        matches = []
        entity_type = conditions.get("entity_type", "MONEY")
        operator = conditions.get("operator", "greater_than")
        threshold = conditions.get("value", 0)
        
        for entity in email.entities:
            if entity.type != entity_type:
                continue
            
            # Try to extract numeric value
            value = self._extract_numeric_value(entity.text)
            if value is None:
                continue
            
            triggered = False
            if operator == "greater_than" and value > threshold:
                triggered = True
            elif operator == "less_than" and value < threshold:
                triggered = True
            elif operator == "equals" and value == threshold:
                triggered = True
            
            if triggered:
                matches.append({
                    "entity_id": entity.id,
                    "matched_text": entity.text,
                    "context": entity.sentence
                })
        
        return matches
    
    def _eval_entity_contains(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate entity contains condition."""
        matches = []
        entity_type = conditions.get("entity_type")
        values = [v.lower() for v in conditions.get("values", [])]
        
        for entity in email.entities:
            if entity_type and entity.type != entity_type:
                continue
            
            entity_text_lower = entity.text.lower()
            for value in values:
                if value in entity_text_lower:
                    matches.append({
                        "entity_id": entity.id,
                        "matched_text": entity.text,
                        "context": entity.sentence
                    })
                    break
        
        return matches
    
    def _eval_keyword_entity(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate keyword + entity condition."""
        matches = []
        keywords = [k.lower() for k in conditions.get("keywords", [])]
        entity_types = conditions.get("entity_types", [])
        
        if not email.body:
            return matches
        
        body_lower = email.body.lower()
        
        # Check if any keyword is in the email
        found_keywords = [k for k in keywords if k in body_lower]
        if not found_keywords:
            return matches
        
        # Find entities of the specified types
        for entity in email.entities:
            if entity_types and entity.type not in entity_types:
                continue
            
            matches.append({
                "entity_id": entity.id,
                "matched_text": f"{entity.text} + keywords: {', '.join(found_keywords)}",
                "context": entity.sentence
            })
        
        return matches
    
    def _eval_co_occurrence(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate entity co-occurrence condition."""
        matches = []
        type1 = conditions.get("entity_type_1")
        type2 = conditions.get("entity_type_2")
        same_sentence = conditions.get("same_sentence", True)
        
        entities_type1 = [e for e in email.entities if e.type == type1]
        entities_type2 = [e for e in email.entities if e.type == type2]
        
        if not entities_type1 or not entities_type2:
            return matches
        
        for e1 in entities_type1:
            for e2 in entities_type2:
                if same_sentence:
                    if e1.sentence and e2.sentence and e1.sentence == e2.sentence:
                        matches.append({
                            "matched_text": f"{e1.text} + {e2.text}",
                            "context": e1.sentence
                        })
                else:
                    matches.append({
                        "matched_text": f"{e1.text} + {e2.text}",
                        "context": e1.sentence
                    })
        
        return matches
    
    def _eval_entity_count(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate entity count condition."""
        entity_type = conditions.get("entity_type")
        operator = conditions.get("operator", "greater_than")
        threshold = conditions.get("value", 0)
        
        if entity_type:
            count = len([e for e in email.entities if e.type == entity_type])
        else:
            count = len(email.entities)
        
        triggered = False
        if operator == "greater_than" and count > threshold:
            triggered = True
        elif operator == "less_than" and count < threshold:
            triggered = True
        elif operator == "equals" and count == threshold:
            triggered = True
        
        if triggered:
            return [{
                "matched_text": f"Entity count: {count}",
                "context": f"Email contains {count} entities" + (f" of type {entity_type}" if entity_type else "")
            }]
        
        return []
    
    def _eval_specific_entity(self, email: Email, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate specific entity condition."""
        matches = []
        target_entities = [e.lower() for e in conditions.get("entities", [])]
        
        for entity in email.entities:
            if entity.text.lower() in target_entities:
                matches.append({
                    "entity_id": entity.id,
                    "matched_text": entity.text,
                    "context": entity.sentence
                })
        
        return matches
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text like '$1,000,000' or '50 million'."""
        text = text.lower().replace(",", "").replace("$", "").strip()
        
        # Handle million/billion
        multiplier = 1
        if "billion" in text:
            multiplier = 1_000_000_000
            text = text.replace("billion", "").strip()
        elif "million" in text:
            multiplier = 1_000_000
            text = text.replace("million", "").strip()
        elif "thousand" in text:
            multiplier = 1_000
            text = text.replace("thousand", "").strip()
        
        # Extract number
        match = re.search(r'[\d.]+', text)
        if match:
            try:
                return float(match.group()) * multiplier
            except ValueError:
                pass
        
        return None
    
    def get_alert_count(self, status: Optional[str] = None) -> int:
        """Get alert count, optionally filtered by status."""
        query = self.db.query(func.count(Alert.id))
        if status:
            query = query.filter(Alert.status == status)
        return query.scalar()
    
    def seed_default_rules(self):
        """Seed default alert rules."""
        default_rules = [
            {
                "name": "High Value Transaction",
                "description": "Alert when money amounts exceed $1,000,000",
                "severity": "high",
                "conditions": {
                    "type": "entity_threshold",
                    "entity_type": "MONEY",
                    "operator": "greater_than",
                    "value": 1000000
                }
            },
            {
                "name": "Regulatory Mention",
                "description": "Alert when regulatory bodies are mentioned",
                "severity": "high",
                "conditions": {
                    "type": "entity_contains",
                    "entity_type": "ORG",
                    "values": ["SEC", "FBI", "DOJ", "Auditor", "Federal"]
                }
            },
            {
                "name": "Executive Mention",
                "description": "Alert when key executives are mentioned",
                "severity": "medium",
                "conditions": {
                    "type": "specific_entity",
                    "entities": ["Ken Lay", "Jeff Skilling", "Andrew Fastow", "Sherron Watkins"]
                }
            },
            {
                "name": "Sensitive Keywords",
                "description": "Alert when sensitive keywords appear with people",
                "severity": "critical",
                "conditions": {
                    "type": "keyword_entity",
                    "keywords": ["fraud", "illegal", "destroy", "shred", "delete", "hide"],
                    "entity_types": ["PERSON", "ORG"]
                }
            },
            {
                "name": "High Entity Density",
                "description": "Alert when an email has unusually many entities",
                "severity": "low",
                "conditions": {
                    "type": "entity_count",
                    "entity_type": None,
                    "operator": "greater_than",
                    "value": 15
                }
            }
        ]
        
        for rule_data in default_rules:
            # Check if rule already exists
            existing = self.db.query(AlertRule).filter(AlertRule.name == rule_data["name"]).first()
            if not existing:
                rule = AlertRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    severity=rule_data["severity"],
                    enabled=True,
                    conditions=json.dumps(rule_data["conditions"])
                )
                self.db.add(rule)
        
        self.db.commit()

