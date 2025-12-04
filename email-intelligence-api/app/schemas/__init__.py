"""Pydantic schemas for API request/response validation."""
from app.schemas.email import (
    EmailBase, EmailCreate, EmailResponse, EmailListResponse, 
    EmailDetailResponse, EmailFilters
)
from app.schemas.entity import (
    EntityBase, EntityResponse, EntityListResponse,
    EntityTypeStats, EntityCoOccurrence
)
from app.schemas.alert import (
    AlertRuleBase, AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertResponse, AlertListResponse, AlertUpdate, RuleCondition
)
from app.schemas.search import (
    SemanticSearchRequest, SemanticSearchResponse, SearchResult,
    SimilarEmailRequest, KeywordSearchRequest
)
from app.schemas.analytics import (
    OverviewStats, TimelineData, TopSender, EntityNetworkData
)

__all__ = [
    # Email
    "EmailBase", "EmailCreate", "EmailResponse", "EmailListResponse",
    "EmailDetailResponse", "EmailFilters",
    # Entity
    "EntityBase", "EntityResponse", "EntityListResponse",
    "EntityTypeStats", "EntityCoOccurrence",
    # Alert
    "AlertRuleBase", "AlertRuleCreate", "AlertRuleUpdate", "AlertRuleResponse",
    "AlertResponse", "AlertListResponse", "AlertUpdate", "RuleCondition",
    # Search
    "SemanticSearchRequest", "SemanticSearchResponse", "SearchResult",
    "SimilarEmailRequest", "KeywordSearchRequest",
    # Analytics
    "OverviewStats", "TimelineData", "TopSender", "EntityNetworkData",
]

