"""Database connections for SQLite and ChromaDB."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

# Ensure data directory exists
os.makedirs(os.path.dirname(settings.sqlite_db_path), exist_ok=True)
os.makedirs(settings.chroma_db_path, exist_ok=True)

# SQLite setup
SQLITE_URL = f"sqlite:///{settings.sqlite_db_path}"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ChromaDB setup
chroma_client = chromadb.PersistentClient(
    path=settings.chroma_db_path,
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)


def get_chroma_collection(name: str = "email_embeddings"):
    """
    Get or create a ChromaDB collection.
    
    Distance metrics:
    - cosine: Best for text embeddings (default)
    - l2: Euclidean distance, best for spatial data
    - ip: Inner product, best for pre-normalized embeddings
    """
    return chroma_client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": settings.vector_distance_metric}
    )


def init_db():
    """Initialize the database tables."""
    from app.models import email, entity, alert, smart_alert, volume_alert, smarsh_alert  # noqa
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Reset the database (for development)."""
    from app.models import email, entity, alert, smart_alert, volume_alert, smarsh_alert  # noqa
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Reset ChromaDB
    chroma_client.reset()
