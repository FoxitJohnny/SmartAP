"""
Database Test Fixtures

Provides test database setup, session management, and cleanup utilities.
Supports both in-memory SQLite (fast) and PostgreSQL (integration) testing.
"""

import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import StaticPool, NullPool

from src.db.models import Base


# Test database URLs
SQLITE_TEST_URL = "sqlite+aiosqlite:///:memory:"
POSTGRES_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/smartap_test"
)


class TestDatabaseManager:
    """
    Manages test database lifecycle.
    
    Supports both in-memory SQLite for fast unit tests and
    PostgreSQL for integration tests.
    
    Usage:
        async with TestDatabaseManager() as db:
            async with db.session() as session:
                # Run tests with session
                pass
    """
    
    def __init__(
        self,
        use_postgres: bool = False,
        echo: bool = False,
    ):
        """
        Initialize test database manager.
        
        Args:
            use_postgres: If True, use PostgreSQL instead of SQLite
            echo: If True, log all SQL statements
        """
        self.use_postgres = use_postgres
        self.echo = echo
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker] = None
    
    @property
    def database_url(self) -> str:
        """Get the appropriate database URL."""
        if self.use_postgres:
            return POSTGRES_TEST_URL
        return SQLITE_TEST_URL
    
    async def __aenter__(self) -> "TestDatabaseManager":
        """Set up test database."""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Tear down test database."""
        await self.teardown()
    
    async def setup(self):
        """Create engine and tables."""
        if self.use_postgres:
            self._engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                poolclass=NullPool,  # Don't pool connections in tests
            )
        else:
            # SQLite in-memory with StaticPool for connection sharing
            self._engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        
        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        # Create all tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def teardown(self):
        """Drop tables and dispose engine."""
        if self._engine:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await self._engine.dispose()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a test session with automatic rollback.
        
        Changes are rolled back after the context exits,
        keeping tests isolated.
        """
        if not self._session_maker:
            raise RuntimeError("Database not initialized. Call setup() first.")
        
        async with self._session_maker() as session:
            try:
                yield session
            finally:
                await session.rollback()
    
    @asynccontextmanager
    async def session_commit(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a test session that commits changes.
        
        Use when you need changes to persist across operations.
        """
        if not self._session_maker:
            raise RuntimeError("Database not initialized. Call setup() first.")
        
        async with self._session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def reset(self):
        """Reset database by dropping and recreating all tables."""
        if self._engine:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)


async def create_test_tables(engine: AsyncEngine):
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_tables(engine: AsyncEngine):
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def override_get_session(test_session: AsyncSession):
    """
    Create a FastAPI dependency override for get_session.
    
    Usage in tests:
        app.dependency_overrides[get_session] = override_get_session(test_session)
    """
    async def _override():
        yield test_session
    
    return _override


# Pytest fixtures (import in conftest.py)

def get_test_engine_fixture(use_postgres: bool = False):
    """
    Factory for creating test engine pytest fixtures.
    
    Usage in conftest.py:
        @pytest.fixture(scope="function")
        async def test_engine():
            return await get_test_engine_fixture()
    """
    import pytest
    
    @pytest.fixture(scope="function")
    async def test_engine():
        manager = TestDatabaseManager(use_postgres=use_postgres)
        await manager.setup()
        yield manager._engine
        await manager.teardown()
    
    return test_engine


def get_test_session_fixture():
    """
    Factory for creating test session pytest fixtures.
    
    Usage in conftest.py:
        test_session = get_test_session_fixture()
    """
    import pytest
    
    @pytest.fixture(scope="function")
    async def test_session(test_engine):
        session_maker = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_maker() as session:
            yield session
            await session.rollback()
    
    return test_session
