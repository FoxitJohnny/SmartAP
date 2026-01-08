"""
Database Seeding CLI

Run: python -m src.db.seed

Seeds the database with test vendors and purchase orders.
"""

import asyncio
from .database import async_session_maker, init_db
from .seed_data import run_seed


async def main():
    """Initialize database and run seed data."""
    print("SmartAP Database Seeding")
    print("=" * 50)
    
    # Initialize database tables
    print("\nInitializing database tables...")
    await init_db()
    print("✓ Tables created")
    
    # Seed data
    print("\n" + "=" * 50)
    async with async_session_maker() as session:
        await run_seed(session)
    
    print("\n" + "=" * 50)
    print("✓ Database ready for development!")


if __name__ == "__main__":
    asyncio.run(main())
