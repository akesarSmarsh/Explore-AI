"""Alert Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


# Rule condition types
class EntityThresholdCondition(BaseModel):
    """Condition for entity value threshold (e.g., MONEY > 1000000)."""
    type: Literal["entity_threshold"] = "entity_threshold"
    entity_type: str  # MONEY, etc.
    operator: str  # greater_than, less_than, equals
    value: float


class EntityContainsCondition(BaseModel):
    """Condition for entity containing specific values."""
    type: Literal["entity_contains"] = "entity_contains"
    entity_type: str  # ORG, PERSON, etc.
    values: List[str]  # ["SEC", "FBI", "DOJ"]


class KeywordEntityCondition(BaseModel):
    """Condition for keyword + entity co-occurrence."""
    type: Literal["keyword_entity"] = "keyword_entity"
    keywords: List[str]  # ["fraud", "illegal"]
    entity_types: List[str]  # ["PERSON", "ORG"]


class CoOccurrenceCondition(BaseModel):
    """Condition for entity type co-occurrence."""
    type: Literal["co_occurrence"] = "co_occurrence"
    entity_type_1: str
    entity_type_2: str
    same_sentence: bool = True


class EntityCountCondition(BaseModel):
    """Condition for entity count in email."""
    type: Literal["entity_count"] = "entity_count"
    entity_type: Optional[str] = None  # None means all types
    operator: str  # greater_than, less_than, equals
    value: int


class SpecificEntityCondition(BaseModel):
    """Condition for specific named entities."""
    type: Literal["specific_entity"] = "specific_entity"
    entities: List[str]  # ["Ken Lay", "Jeff Skilling"]


RuleCondition = Union[
    EntityThresholdCondition,
    EntityContainsCondition,
    KeywordEntityCondition,
    CoOccurrenceCondition,
    EntityCountCondition,
    SpecificEntityCondition
]


class AlertRuleBase(BaseModel):
    """Base alert rule schema."""
    name: str
    description: Optional[str] = None
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    enabled: bool = True


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule."""
    conditions: RuleCondition


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    conditions: Optional[RuleCondition] = None


class AlertRuleResponse(AlertRuleBase):
    """Alert rule response schema."""
    id: str
    conditions: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MatchedEntity(BaseModel):
    """Matched entity in alert."""
    text: str
    type: str


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str
    triggered_at: datetime
    email_id: str
    email_subject: Optional[str] = None
    matched_entities: List[MatchedEntity] = []
    context: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""
    total: int
    alerts: List[AlertResponse]


class AlertUpdate(BaseModel):
    """Schema for updating alert status."""
    status: str = Field(pattern="^(active|acknowledged|dismissed)$")


class AlertFilters(BaseModel):
    """Alert query filters."""
    status: Optional[str] = None
    severity: Optional[str] = None
    rule_id: Optional[str] = None
    date_from: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=200)

