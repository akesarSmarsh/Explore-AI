"""Search service for semantic and keyword search."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Email, Entity
from app.core.embeddings import embedding_processor
from app.core.vector_store import vector_store
from app.schemas.search import (
    SemanticSearchRequest, SearchResult, SearchFilters,
    KeywordSearchRequest, SimilarEmailRequest
)


class SearchService:
    """Service for search operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def semantic_search(self, request: SemanticSearchRequest) -> List[SearchResult]:
        """
        Perform semantic search on emails.
        
        Args:
            request: Search request with query and filters
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = embedding_processor.encode(request.query)
        
        # Build metadata filter for ChromaDB
        where_filter = None
        if request.filters:
            where_filter = self._build_chroma_filter(request.filters)
        
        # Search in vector store
        search_results = vector_store.search(
            query_embedding=query_embedding,
            n_results=request.limit * 2,  # Get extra for post-filtering
            where=where_filter
        )
        
        # Get email details and apply additional filters
        results = []
        for i, email_id in enumerate(search_results["ids"]):
            email = self.db.query(Email).filter(Email.id == email_id).first()
            if not email:
                continue
            
            # Apply date filters if not handled by ChromaDB
            if request.filters:
                if request.filters.date_from and email.date:
                    # Compare dates, handling timezone-naive datetimes
                    email_date = email.date.replace(tzinfo=None) if email.date.tzinfo else email.date
                    filter_from = request.filters.date_from.replace(tzinfo=None) if request.filters.date_from.tzinfo else request.filters.date_from
                    if email_date < filter_from:
                        continue
                if request.filters.date_to and email.date:
                    # Compare dates, handling timezone-naive datetimes
                    # Add 1 day to date_to to include the entire end day
                    email_date = email.date.replace(tzinfo=None) if email.date.tzinfo else email.date
                    filter_to = request.filters.date_to.replace(tzinfo=None) if request.filters.date_to.tzinfo else request.filters.date_to
                    # If date_to has no time component (00:00:00), include the entire day
                    if filter_to.hour == 0 and filter_to.minute == 0 and filter_to.second == 0:
                        filter_to = filter_to + timedelta(days=1) - timedelta(seconds=1)
                    if email_date > filter_to:
                        continue
            
            # Calculate relevance score (1 - distance for cosine)
            distance = search_results["distances"][i] if search_results["distances"] else 0
            relevance_score = 1 - distance
            
            # Get snippet
            snippet = self._get_snippet(email.body, request.query) if email.body else None
            
            # Get matched entities
            matched_entities = [e.text for e in email.entities[:5]]
            
            results.append(SearchResult(
                email_id=email.id,
                subject=email.subject,
                sender=email.sender,
                date=email.date,
                relevance_score=round(relevance_score, 4),
                snippet=snippet,
                matched_entities=matched_entities
            ))
            
            if len(results) >= request.limit:
                break
        
        return results
    
    def find_similar(self, request: SimilarEmailRequest) -> List[SearchResult]:
        """
        Find emails similar to a given email.
        
        Args:
            request: Request with source email ID
            
        Returns:
            List of similar emails
        """
        similar = vector_store.find_similar(
            id=request.email_id,
            n_results=request.limit
        )
        
        results = []
        for item in similar:
            email = self.db.query(Email).filter(Email.id == item["id"]).first()
            if not email:
                continue
            
            results.append(SearchResult(
                email_id=email.id,
                subject=email.subject,
                sender=email.sender,
                date=email.date,
                relevance_score=round(item["score"], 4) if item["score"] else 0,
                snippet=email.body[:200] if email.body else None,
                matched_entities=[]
            ))
        
        return results
    
    def keyword_search(
        self,
        request: KeywordSearchRequest
    ) -> tuple[List[SearchResult], int]:
        """
        Perform keyword search on emails.
        
        Args:
            request: Search request
            
        Returns:
            Tuple of (results, total count)
        """
        query = self.db.query(Email)
        
        # Search in subject and body
        search_term = f"%{request.query}%"
        query = query.filter(
            or_(
                Email.subject.ilike(search_term),
                Email.body.ilike(search_term)
            )
        )
        
        # Apply filters
        if request.filters:
            if request.filters.date_from:
                query = query.filter(Email.date >= request.filters.date_from)
            if request.filters.date_to:
                query = query.filter(Email.date <= request.filters.date_to)
            if request.filters.sender:
                query = query.filter(Email.sender.ilike(f"%{request.filters.sender}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (request.page - 1) * request.limit
        emails = query.order_by(Email.date.desc()).offset(offset).limit(request.limit).all()
        
        results = []
        for email in emails:
            snippet = self._get_snippet(email.body, request.query) if email.body else None
            
            results.append(SearchResult(
                email_id=email.id,
                subject=email.subject,
                sender=email.sender,
                date=email.date,
                relevance_score=1.0,  # Keyword match
                snippet=snippet,
                matched_entities=[]
            ))
        
        return results, total
    
    def _build_chroma_filter(self, filters: SearchFilters) -> Optional[Dict[str, Any]]:
        """Build ChromaDB metadata filter."""
        conditions = []
        
        if filters.sender:
            conditions.append({"sender": {"$eq": filters.sender}})
        
        if not conditions:
            return None
        
        if len(conditions) == 1:
            return conditions[0]
        
        return {"$and": conditions}
    
    def _get_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Extract a relevant snippet from text."""
        if not text:
            return ""
        
        # Find query in text
        query_lower = query.lower()
        text_lower = text.lower()
        
        pos = text_lower.find(query_lower)
        if pos == -1:
            # Query not found, return beginning
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # Extract snippet around the match
        start = max(0, pos - max_length // 2)
        end = min(len(text), pos + len(query) + max_length // 2)
        
        snippet = text[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet

