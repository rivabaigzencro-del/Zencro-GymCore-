import logging
import re
from typing import Generator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("gymcore.database")

# Dialect-aware engine configuration
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": False,  # Never log raw SQL containing credentials in production
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL / Supabase pooler connection tuning
    engine_kwargs["pool_pre_ping"] = True      # Check connection liveliness before checkout
    engine_kwargs["pool_recycle"] = 300       # Recycle connections every 5 minutes (prevents stale pooler connections)
    engine_kwargs["pool_size"] = 5            # Sensible pool size for Supabase transaction/session pooler
    engine_kwargs["max_overflow"] = 10        # Max burst connections
    engine_kwargs["connect_args"] = {
        "connect_timeout": 10,                # Fail fast (10s) instead of hanging indefinitely on dead connections
    }

engine: Engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

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


def get_safe_database_url(target_engine: Optional[Engine] = None) -> str:
    """Return the database URL with any password sanitized/masked."""
    current_engine = target_engine or engine
    try:
        return current_engine.url.render_as_string(hide_password=True)
    except Exception:
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", settings.DATABASE_URL)


def check_database_connection(target_engine: Optional[Engine] = None) -> Tuple[bool, Optional[str]]:
    """
    Safely verify database connectivity with timeout and safe diagnostics.
    Returns (is_healthy, safe_diagnostic_message).
    Never exposes passwords, tokens or credentials.
    """
    current_engine = target_engine or engine
    safe_target = get_safe_database_url(current_engine)

    # 1. Check if production environment is mistakenly pointing to localhost
    db_url_lower = str(current_engine.url).lower() if hasattr(current_engine, "url") else settings.DATABASE_URL.lower()
    if settings.ENV == "production" and any(h in db_url_lower for h in ["localhost", "127.0.0.1"]):
        msg = (
            "DATABASE_URL environment variable is not configured in production (defaulted to localhost:5432). "
            "Please configure DATABASE_URL in your Render Dashboard (Environment tab)."
        )
        logger.warning("Database configuration check: %s", msg)
        return False, msg

    # 2. Check for known direct Supabase hostname incompatibility (IPv6 only)
    if "supabase.co" in db_url_lower and "pooler.supabase.com" not in db_url_lower:
        msg = (
            "Direct Supabase host detected (db.*.supabase.co). Supabase direct hosts only resolve to IPv6, "
            "which Render does not route. Use the Supabase Session/Transaction Pooler URL instead "
            "(e.g., aws-0-<region>.pooler.supabase.com:5432 or :6543)."
        )
        logger.warning("Database configuration check: %s", msg)
        return False, msg

    # 3. Perform live query ping
    try:
        with current_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        raw_err = str(exc)
        # Redact any passwords that might appear in the raw exception
        sanitized_err = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", raw_err)
        sanitized_err = re.sub(r"password=[^\s]+", "password=***", sanitized_err)

        logger.error("Database connectivity check failed for [%s]: %s", safe_target, sanitized_err)

        # Classify the error for safe human-readable diagnosis without leaking secrets
        err_lower = sanitized_err.lower()
        if "password authentication failed" in err_lower:
            detail = "Database authentication failed: incorrect user or password in DATABASE_URL."
        elif "no pg_hba.conf entry" in err_lower or "no encryption" in err_lower:
            detail = "Database requires SSL encryption. Append '?sslmode=require' to DATABASE_URL in Render."
        elif any(term in err_lower for term in ["could not translate host name", "getaddrinfo failed", "name or service not known"]):
            detail = "Database host resolution failed. Check the hostname in DATABASE_URL."
        elif "connection refused" in err_lower:
            detail = "Database connection was refused. Check host and port."
        elif "timeout" in err_lower or "timed out" in err_lower:
            detail = "Database connection timed out. Check network connectivity, firewall, or pooler status."
        else:
            detail = f"Database connection error: {exc.__class__.__name__}"

        return False, detail
