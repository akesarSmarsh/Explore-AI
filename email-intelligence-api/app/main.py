"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Email Intelligence API - NER-powered email analysis with smart alerts.
    
    ## Features
    
    - **Email Processing**: Parse and store emails with automatic NER extraction
    - **Named Entity Recognition**: Extract people, organizations, locations, money, dates, etc.
    - **Semantic Search**: Natural language search using AI embeddings
    - **Smart Alerts**: Customizable rules to detect important patterns
    - **Analytics**: Dashboard statistics and visualizations
    
    ## Quick Start
    
    1. Initialize the database: `POST /api/v1/system/init`
    2. Upload emails: `POST /api/v1/emails/upload`
    3. Search emails: `POST /api/v1/search/semantic`
    4. View alerts: `GET /api/v1/alerts`
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    # Initialize database tables
    init_db()
    
    # Load BM25 index if hybrid search is enabled
    if settings.enable_hybrid_search:
        from app.core.bm25_search import bm25_search
        if bm25_search.load_index():
            print("🔍 BM25 index loaded for hybrid search")
        else:
            print("⚠️  BM25 index not found. Run scripts/build_bm25_index.py to enable hybrid search")
    
    # Start background scheduler
    if settings.enable_scheduler:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.start()
        print("📅 Background scheduler started")
    
    print(f"🚀 {settings.app_name} v{settings.app_version} started")
    print(f"📚 API docs available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if settings.enable_scheduler:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.shutdown()
        print("📅 Background scheduler stopped")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/system/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )

