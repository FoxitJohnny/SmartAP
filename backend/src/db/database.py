"""
SmartAP Database Configuration

SQLAlchemy async engine and session management with connection pooling.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
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
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
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
