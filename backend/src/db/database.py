"""
SmartAP Database Configuration

SQLAlchemy async engine and session management with connection pooling.
Also provides synchronous SessionLocal for background tasks (e.g., APScheduler).
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import get_settings

settings = get_settings()

# Determine pool class based on database type
# SQLite doesn't support connection pooling in async mode
is_sqlite = "sqlite" in settings.database_url

# Connection pool configuration for PostgreSQL
# For async engines, we don't specify poolclass - SQLAlchemy handles it
pool_config = {}
if not is_sqlite:
    pool_config = {
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_pool_max_overflow,
        "pool_timeout": settings.database_pool_timeout,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
    }
else:
    pool_config = {"poolclass": NullPool}

# Create async engine with optimized configuration
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    **pool_config,
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ============================================================
# Synchronous engine and SessionLocal for background tasks
# (APScheduler jobs, ERP sync, etc.)
# ============================================================

def _get_sync_database_url() -> str:
    """Convert async database URL to sync URL."""
    url = settings.database_url
    # Convert postgresql+asyncpg:// to postgresql://
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    # Convert sqlite+aiosqlite:// to sqlite://
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://")
    return url

# Sync pool config (simpler than async)
sync_pool_config = {}
if not is_sqlite:
    sync_pool_config = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }

# Create synchronous engine for background tasks
sync_engine = create_engine(
    _get_sync_database_url(),
    echo=settings.database_echo,
    **sync_pool_config,
)

# Synchronous session factory for background jobs
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


def get_sync_session() -> Session:
    """
    Get a synchronous database session.
    
    Use for background tasks that can't be async (APScheduler, etc.)
    Remember to close the session when done!
    
    Usage:
        db = get_sync_session()
        try:
            # do work
            db.commit()
        finally:
            db.close()
    """
    return SessionLocal()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    
    This creates all tables defined in the SQLAlchemy models.
    Should be called on application startup.
    """
    from .models import Base
    from sqlalchemy import inspect, text

    def _ensure_additive_schema(sync_conn) -> None:
        """Apply additive schema updates for existing databases.

        This project uses `create_all()` on startup; that won't add new columns.
        We keep this strictly additive (ADD COLUMN / CREATE TABLE) to be safe.
        """
        inspector = inspect(sync_conn)
        tables = set(inspector.get_table_names())

        # Add ai_evaluation JSON column for persisted AI decisions
        if "matching_results" in tables:
            existing_cols = {c["name"] for c in inspector.get_columns("matching_results")}
            if "ai_evaluation" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE matching_results ADD COLUMN ai_evaluation JSON"))

        # Add new columns to matching_settings if the table already exists
        if "matching_settings" in tables:
            existing_cols = {c["name"] for c in inspector.get_columns("matching_settings")}
            if "good_match_threshold" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE matching_settings ADD COLUMN good_match_threshold FLOAT"))
            if "amount_match_tolerance" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE matching_settings ADD COLUMN amount_match_tolerance FLOAT"))

        # Add new risk assessment columns (v2.0 enhancement)
        if "risk_assessments" in tables:
            existing_cols = {c["name"] for c in inspector.get_columns("risk_assessments")}
            if "matching_risk_score" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE risk_assessments ADD COLUMN matching_risk_score FLOAT"))
            if "vendor_risk_info" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE risk_assessments ADD COLUMN vendor_risk_info JSON"))
            if "price_anomaly_info" not in existing_cols:
                sync_conn.execute(text("ALTER TABLE risk_assessments ADD COLUMN price_anomaly_info JSON"))
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        # Apply additive migrations for existing DBs
        await conn.run_sync(_ensure_additive_schema)
        print("✅ Database tables created successfully")


async def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    Use only for testing or reset scenarios.
    """
    from .models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("⚠️  All database tables dropped")
