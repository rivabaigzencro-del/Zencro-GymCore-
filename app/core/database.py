from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Engine configuration with connection pooling and health pre-ping
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Check connection liveliness before checkout
    pool_recycle=300,        # Recycle connections every 5 minutes (prevents stale pooler connections)
    pool_size=5,             # Sensible pool size for Supabase transaction/session pooler
    max_overflow=10,         # Max burst connections
    echo=False,              # Never log raw SQL containing potential credentials in production
)

# Session factory for handling requests
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative Base for all SQLAlchemy models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to provide a transactional database session per request."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
